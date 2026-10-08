import 'package:flutter_hbb/common/hbbs/hbbs.dart';
import 'package:flutter_hbb/models/peer_model.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('peers accept multiple groups and retain legacy primary group', () {
    final peer = Peer.fromJson({
      'id': '123456',
      'device_group_name': 'Operations',
      'device_group_names': ['Operations', 'Support'],
    });
    expect(peer.device_group_name, 'Operations');
    expect(peer.device_group_names, ['Operations', 'Support']);
    expect(Peer.fromJson(peer.toJson()).device_group_names,
        ['Operations', 'Support']);
    expect(Peer.copy(peer).device_group_names, ['Operations', 'Support']);
    expect(peer.toGroupCacheJson()['device_group_names'],
        ['Operations', 'Support']);
  });

  test('older servers with single group still populate group list', () {
    final old = Peer.fromJson({
      'id': '876543',
      'device_group_name': 'Legacy',
    });
    expect(old.device_group_names, ['Legacy']);
  });

  test('server peer payload maps all groups into the client peer model', () {
    final payload = PeerPayload.fromJson({
      'id': '991100',
      'user_name': 'alice',
      'info': {'os': 'Linux', 'device_name': 'Workstation'},
      'device_group_name': 'Operations',
      'device_group_names': ['Operations', 'Support'],
    });
    final peer = PeerPayload.toPeer(payload);
    expect(peer.device_group_names, ['Operations', 'Support']);
    expect(peer.loginName, 'alice');
  });
}
