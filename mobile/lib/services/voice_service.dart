import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:record/record.dart';

/// Live Tamil voice input via Muse Voice Transcribe. Streams microphone audio
/// over a WebSocket to the backend /voice/stream relay at 24000 Hz.
class VoiceService {
  final AudioRecorder _recorder = AudioRecorder();
  WebSocketChannel? _channel;
  final _transcriptController = StreamController<String>.broadcast();

  Stream<String> get transcriptStream => _transcriptController.stream;

  Future<void> startListening(String wsUrl) async {
    if (!await _recorder.hasPermission()) {
      throw Exception('Microphone permission denied');
    }
    _channel = WebSocketChannel.connect(Uri.parse(wsUrl));

    _channel!.stream.listen((message) {
      try {
        final data = jsonDecode(message as String);
        if (data['type'] == 'final_transcript' || data['type'] == 'partial_transcript') {
          _transcriptController.add(data['text'] as String);
        }
      } catch (_) {}
    });

    // Muse Voice Transcribe expects mono 16-bit PCM at 24 kHz
    final stream = await _recorder.startStream(
      const RecordConfig(encoder: AudioEncoder.pcm16bits, sampleRate: 24000, numChannels: 1),
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
