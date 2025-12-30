import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../services/config_service.dart';

/// Setup screen for configuring the app on first launch.
/// Allows users to enter server URL and optional Porcupine access key.
class SetupScreen extends StatefulWidget {
  final ConfigService configService;
  final VoidCallback onConfigured;

  const SetupScreen({
    super.key,
    required this.configService,
    required this.onConfigured,
  });

  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _serverUrlController = TextEditingController();
  final _porcupineKeyController = TextEditingController();
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    // Pre-populate with existing values if editing
    _serverUrlController.text = widget.configService.serverUrl;
    _porcupineKeyController.text = widget.configService.porcupineAccessKey;
  }

  @override
  void dispose() {
    _serverUrlController.dispose();
    _porcupineKeyController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isSaving = true);

    try {
      await widget.configService.setServerUrl(_serverUrlController.text);
      await widget.configService.setPorcupineAccessKey(_porcupineKeyController.text);
      widget.onConfigured();
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }

  Future<void> _openPicovoiceConsole() async {
    final uri = Uri.parse('https://console.picovoice.ai/');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1A1A1A),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 36),
            child: Form(
              key: _formKey,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Header
                  const Icon(
                    Icons.graphic_eq,
                    size: 80,
                    color: Colors.white,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'CAAL Setup',
                    style: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Configure your connection settings',
                    style: TextStyle(
                      fontSize: 16,
                      color: Colors.white70,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 40),

                  // Server URL field
                  const Text(
                    'Server URL *',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextFormField(
                    controller: _serverUrlController,
                    keyboardType: TextInputType.url,
                    autocorrect: false,
                    style: const TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      hintText: 'http://192.168.1.100:3000',
                      filled: true,
                      fillColor: const Color(0xFF2A2A2A),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide.none,
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 14,
                      ),
                    ),
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return 'Server URL is required';
                      }
                      final uri = Uri.tryParse(value.trim());
                      if (uri == null || !uri.hasScheme || !uri.hasAuthority) {
                        return 'Enter a valid URL (e.g., http://192.168.1.100:3000)';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Your CAAL server address',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.white54,
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Porcupine Access Key field
                  const Text(
                    'Porcupine Access Key',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    '(optional)',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.white54,
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextFormField(
                    controller: _porcupineKeyController,
                    autocorrect: false,
                    style: const TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      hintText: 'Enter your Picovoice access key',
                      filled: true,
                      fillColor: const Color(0xFF2A2A2A),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide.none,
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 14,
                      ),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      const Expanded(
                        child: Text(
                          'For "Hey Cal" wake word detection',
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.white54,
                          ),
                        ),
                      ),
                      GestureDetector(
                        onTap: _openPicovoiceConsole,
                        child: const Text(
                          'Get a free key',
                          style: TextStyle(
                            fontSize: 12,
                            color: Color(0xFF3B82F6),
                            decoration: TextDecoration.underline,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 40),

                  // Save button
                  SizedBox(
                    height: 50,
                    child: TextButton(
                      onPressed: _isSaving ? null : _save,
                      style: TextButton.styleFrom(
                        backgroundColor: const Color(0xFF45997C),
                        foregroundColor: const Color(0xFF171717),
                        disabledForegroundColor: const Color(0xFF171717),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(30),
                        ),
                      ),
                      child: _isSaving
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor: AlwaysStoppedAnimation(Color(0xFF171717)),
                              ),
                            )
                          : const Text(
                              'SAVE & CONNECT',
                              style: TextStyle(fontWeight: FontWeight.bold),
                            ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
