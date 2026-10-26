import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:record/record.dart';

/// Live Tamil voice input/output via Bhashini. Streams microphone audio
/// over a WebSocket for low-latency ASR while the farmer talks, rather
/// than recording-then-uploading (matches the blueprint's "WebSockets for
/// streaming live Tamil audio" requirement).
///
/// The WS URL/inference key must come from your backend's
/// GET /voice/pipeline-config endpoint (add this thin proxy route in
/// backend/app/routers/ if you want to keep BHASHINI_API_KEY off the
/// device — recommended, since anything shipped in the APK is
/// extractable). This class assumes that proxy exists.
class VoiceService {
  final AudioRecorder _recorder = AudioRecorder();
  WebSocketChannel? _channel;
  final _transcriptController = StreamController<String>.broadcast();

  Stream<String> get transcriptStream => _transcriptController.stream;

  Future<void> startListening(String wsUrl, String inferenceKey) async {
    if (!await _recorder.hasPermission()) {
      throw Exception('Microphone permission denied');
    }
    _channel = WebSocketChannel.connect(Uri.parse(wsUrl));
    _channel!.sink.add(jsonEncode({'type': 'auth', 'key': inferenceKey}));

    _channel!.stream.listen((message) {
      final data = jsonDecode(message as String);
      if (data['type'] == 'partial_transcript' || data['type'] == 'final_transcript') {
        _transcriptController.add(data['text'] as String);
      }
    });

    final stream = await _recorder.startStream(
      const RecordConfig(encoder: AudioEncoder.pcm16bits, sampleRate: 16000, numChannels: 1),
    );
    stream.listen((chunk) => _channel?.sink.add(chunk));
  }

  Future<void> stopListening() async {
    await _recorder.stop();
    await _channel?.sink.close();
  }

  void dispose() {
    _transcriptController.close();
    _recorder.dispose();
  }
}
