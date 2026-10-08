import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_hbb/common.dart';
import 'package:flutter_hbb/desktop/widgets/tabbar_widget.dart';
import 'package:flutter_hbb/models/platform_model.dart';
import 'package:get/get.dart';

import '../../utils/http_service.dart' as http;

/// Administration is deliberately a desktop-client page, not a separate web
/// dashboard. The server independently checks the Bearer token's admin role.
class MirvDeskAdminPage extends StatefulWidget {
  const MirvDeskAdminPage({super.key});

  static void open() {
    final tabs = Get.find<DesktopTabController>();
    tabs.add(
      TabInfo(
        key: 'mirvdesk-admin',
        label: 'Administration',
        selectedIcon: Icons.admin_panel_settings,
        unselectedIcon: Icons.admin_panel_settings_outlined,
        page: const MirvDeskAdminPage(key: ValueKey('mirvdesk-admin')),
      ),
    );
  }

  @override
  State<MirvDeskAdminPage> createState() => _MirvDeskAdminPageState();
}

class _MirvDeskAdminPageState extends State<MirvDeskAdminPage> {
  bool loading = false;
  String? error;
  List<Map<String, dynamic>> users = [];
  List<Map<String, dynamic>> groups = [];
  List<Map<String, dynamic>> devices = [];
  List<Map<String, dynamic>> audit = [];

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<Uri> _endpoint(String path) async {
    final base = (await bind.mainGetApiServer()).trim().replaceFirst(
      RegExp(r'/$'),
      '',
    );
    if (base.isEmpty) {
      throw StateError('MirvDesk Server is not configured');
    }
    return Uri.parse(base + path);
  }

  Future<dynamic> _request(String method, String path, [Object? body]) async {
    final uri = await _endpoint(path);
    final headers = {...getHttpHeaders(), 'Content-Type': 'application/json'};
    late final http.Response response;
    switch (method) {
      case 'GET':
        response = await http.get(uri, headers: headers);
        break;
      case 'POST':
        response = await http.post(
          uri,
          headers: headers,
          body: jsonEncode(body),
        );
        break;
      case 'PUT':
        response = await http.put(
          uri,
          headers: headers,
          body: jsonEncode(body),
        );
        break;
      case 'DELETE':
        response = await http.delete(uri, headers: headers);
        break;
      default:
        throw StateError('Unsupported admin request');
    }
    final decoded = jsonDecode(decode_http_response(response));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      if (response.statusCode == 404) {
        throw StateError(
          'Administrator API unavailable. Upgrade MirvDesk Server to 1.7.',
        );
      }
      final message = decoded is Map ? decoded['error'] : null;
      throw StateError(
        message?.toString() ?? 'HTTP ' + response.statusCode.toString(),
      );
    }
    return decoded;
  }

  Future<List<Map<String, dynamic>>> _fetchPaged(String path) async {
    final items = <Map<String, dynamic>>[];
    const perPage = 500;
    for (var current = 1; current <= 20; current++) {
      final page = await _request(
        'GET',
        path +
            '?current=' +
            current.toString() +
            '&pageSize=' +
            perPage.toString(),
      );
      if (page is! Map || page['data'] is! List) {
        throw const FormatException('Invalid MirvDesk admin response');
      }
      for (final item in page['data'] as List) {
        if (item is Map<String, dynamic>) items.add(item);
      }
      final total = page['total'] is int ? page['total'] as int : items.length;
      if (items.length >= total || (page['data'] as List).isEmpty) break;
    }
    return items;
  }

  Future<void> _reload() async {
    if (!gFFI.userModel.isAdmin.value) {
      setState(() {
        error = 'Administrator account required';
        loading = false;
      });
      return;
    }
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final result = await Future.wait([
        _fetchPaged('/api/admin/users'),
        _fetchPaged('/api/admin/groups'),
        _fetchPaged('/api/admin/devices'),
        _fetchPaged('/api/admin/audit'),
      ]);
      if (!mounted) return;
      setState(() {
        users = result[0];
        groups = result[1];
        devices = result[2];
        audit = result[3];
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        error = e.toString();
      });
    } finally {
      if (mounted)
        setState(() {
          loading = false;
        });
    }
  }

  Future<String?> _prompt(String title, String label) async {
    final controller = TextEditingController();
    try {
      return await showDialog<String>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: Text(title),
          content: TextField(
            controller: controller,
            autofocus: true,
            decoration: InputDecoration(labelText: label),
            onSubmitted: (value) =>
                Navigator.of(dialogContext).pop(value.trim()),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () =>
                  Navigator.of(dialogContext).pop(controller.text.trim()),
              child: const Text('Save'),
            ),
          ],
        ),
      );
    } finally {
      controller.dispose();
    }
  }

  Future<void> _mutation(String method, String path, [Object? body]) async {
    try {
      await _request(method, path, body);
      await _reload();
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Saved')));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _createGroup() async {
    final name = await _prompt('New device group', 'Group name');
    if (name == null || name.isEmpty) return;
    await _mutation('POST', '/api/admin/groups', {'name': name});
  }

  Future<void> _editDeviceGroups(Map<String, dynamic> device) async {
    final id = (device['id'] ?? '').toString();
    final selected = <String>{};
    if (device['device_group_names'] is List) {
      selected.addAll(
        (device['device_group_names'] as List).whereType<String>(),
      );
    } else if ((device['device_group_name'] ?? '').toString().isNotEmpty) {
      selected.add(device['device_group_name'].toString());
    }
    final result = await showDialog<List<String>>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) => AlertDialog(
          title: Text('Groups for ' + id),
          content: SizedBox(
            width: 380,
            child: ListView(
              shrinkWrap: true,
              children: [
                for (final group in groups)
                  CheckboxListTile(
                    title: Text((group['name'] ?? '').toString()),
                    value: selected.contains(group['name']),
                    onChanged: (checked) {
                      setDialogState(() {
                        final name = (group['name'] ?? '').toString();
                        if (checked == true) {
                          selected.add(name);
                        } else {
                          selected.remove(name);
                        }
                      });
                    },
                  ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () =>
                  Navigator.of(dialogContext).pop(selected.toList()),
              child: const Text('Save'),
            ),
          ],
        ),
      ),
    );
    if (result == null) return;
    await _mutation(
      'PUT',
      '/api/admin/devices/' + Uri.encodeComponent(id) + '/groups',
      {'groups': result},
    );
  }

  Future<void> _changeMember(String groupName, bool add) async {
    final username = await _prompt(
      add ? 'Add user to group' : 'Remove user from group',
      'Username',
    );
    if (username == null || username.isEmpty) return;
    final path =
        '/api/admin/groups/' +
        Uri.encodeComponent(groupName) +
        '/members' +
        (add ? '' : '/' + Uri.encodeComponent(username));
    await _mutation(
      add ? 'POST' : 'DELETE',
      path,
      add ? {'username': username} : null,
    );
  }

  Widget _userList() => ListView.builder(
    itemCount: users.length,
    itemBuilder: (context, i) {
      final user = users[i];
      return ListTile(
        leading: const Icon(Icons.person_outline),
        title: Text((user['display_name'] ?? user['name'] ?? '').toString()),
        subtitle: Text('@' + (user['name'] ?? '').toString()),
        trailing: Text(
          user['is_admin'] == true
              ? 'Admin'
              : (user['status'] == 1 ? 'Active' : 'Disabled'),
        ),
      );
    },
  );

  Widget _groupList() => Column(
    children: [
      Align(
        alignment: Alignment.centerRight,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: FilledButton.icon(
            icon: const Icon(Icons.add),
            label: const Text('Create group'),
            onPressed: _createGroup,
          ),
        ),
      ),
      Expanded(
        child: ListView.builder(
          itemCount: groups.length,
          itemBuilder: (context, i) {
            final name = (groups[i]['name'] ?? '').toString();
            return ListTile(
              leading: const Icon(Icons.folder_outlined),
              title: Text(name),
              subtitle: const Text('Device access visibility group'),
              trailing: Wrap(
                spacing: 4,
                children: [
                  TextButton(
                    onPressed: () => _changeMember(name, true),
                    child: const Text('Add member'),
                  ),
                  TextButton(
                    onPressed: () => _changeMember(name, false),
                    child: const Text('Remove member'),
                  ),
                ],
              ),
            );
          },
        ),
      ),
    ],
  );

  Widget _deviceList() => ListView.builder(
    itemCount: devices.length,
    itemBuilder: (context, i) {
      final device = devices[i];
      final names = device['device_group_names'] is List
          ? (device['device_group_names'] as List).join(', ')
          : (device['device_group_name'] ?? '').toString();
      return ListTile(
        leading: const Icon(Icons.desktop_windows_outlined),
        title: Text((device['id'] ?? '').toString()),
        subtitle: Text(
          'Owner: ' +
              (device['user_name'] ?? '').toString() +
              (names.isEmpty ? '' : ' · ' + names),
        ),
        trailing: OutlinedButton(
          onPressed: () => _editDeviceGroups(device),
          child: const Text('Edit groups'),
        ),
      );
    },
  );

  Widget _auditList() => ListView.builder(
    itemCount: audit.length,
    itemBuilder: (context, i) {
      final entry = audit[i];
      final seconds = entry['created_at'] is int
          ? entry['created_at'] as int
          : 0;
      final time = seconds > 0
          ? DateTime.fromMillisecondsSinceEpoch(seconds * 1000).toLocal()
          : null;
      return ListTile(
        leading: const Icon(Icons.history_outlined),
        title: Text((entry['action'] ?? '').toString()),
        subtitle: Text(
          (entry['actor'] ?? '').toString() +
              ' · ' +
              (entry['target_type'] ?? '').toString() +
              ': ' +
              (entry['target_id'] ?? '').toString(),
        ),
        trailing: time == null ? null : Text(time.toString().substring(0, 16)),
      );
    },
  );

  @override
  Widget build(BuildContext context) => DefaultTabController(
    length: 4,
    child: Scaffold(
      appBar: AppBar(
        title: const Text('MirvDesk administration'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            icon: const Icon(Icons.refresh),
            onPressed: loading ? null : _reload,
          ),
        ],
        bottom: const TabBar(
          tabs: [
            Tab(icon: Icon(Icons.people_outline), text: 'Users'),
            Tab(icon: Icon(Icons.folder_outlined), text: 'Groups'),
            Tab(icon: Icon(Icons.computer_outlined), text: 'Devices'),
            Tab(icon: Icon(Icons.history_outlined), text: 'Audit'),
          ],
        ),
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : error != null
          ? Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(error!, textAlign: TextAlign.center),
                  const SizedBox(height: 12),
                  OutlinedButton(
                    onPressed: _reload,
                    child: const Text('Retry'),
                  ),
                ],
              ),
            )
          : TabBarView(
              children: [
                _userList(),
                _groupList(),
                _deviceList(),
                _auditList(),
              ],
            ),
    ),
  );
}
