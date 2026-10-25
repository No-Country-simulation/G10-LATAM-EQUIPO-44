import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import '../models/selected_document.dart';
import '../design_system/app_spacing.dart';
import '../widgets/app_components.dart';

enum PhotoReviewDecision { confirm, retake }

// Agregado por Edil: revisar legibilidad antes de aceptar; no es OCR ni envio.
class PhotoReviewScreen extends StatefulWidget {
  const PhotoReviewScreen({super.key, required this.document});
  final SelectedDocument document;

  @override
  State<PhotoReviewScreen> createState() => _PhotoReviewScreenState();
}

class _PhotoReviewScreenState extends State<PhotoReviewScreen> {
  late final Future<bool> _readable = _checkImage();

  Future<bool> _checkImage() async {
    try {
      final codec = await ui.instantiateImageCodec(widget.document.bytes!);
      final frame = await codec.getNextFrame();
      frame.image.dispose();
      codec.dispose();
      return true;
    } catch (_) {
      return false;
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Revisar foto')),
    body: SafeArea(
      child: FutureBuilder<bool>(
        future: _readable,
        builder: (context, snapshot) => ListView(
          padding: EdgeInsets.all(
            MediaQuery.sizeOf(context).width < 400
                ? AppSpacing.lg
                : AppSpacing.xl,
          ),
          children: [
            const AppHeader(
              title: 'Confirma la legibilidad',
              subtitle:
                  'Comprueba que se vea el documento completo, con letras claras y sin reflejos. Puedes ampliar la imagen.',
            ),
            const SizedBox(height: AppSpacing.lg),
            AppCard(
              padding: AppSpacing.sm,
              child: SizedBox(
                height: 320,
                child: snapshot.data == true
                    ? InteractiveViewer(
                        child: Image.memory(
                          widget.document.bytes!,
                          fit: BoxFit.contain,
                        ),
                      )
                    : Center(
                        child: snapshot.connectionState != ConnectionState.done
                            ? const CircularProgressIndicator()
                            : const Text(
                                'No se puede visualizar esta foto. Repite la captura.',
                              ),
                      ),
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
            AppButton(
              onPressed: snapshot.data == true
                  ? () => Navigator.pop(context, PhotoReviewDecision.confirm)
                  : null,
              icon: Icons.check,
              label: 'Usar esta foto',
            ),
            const SizedBox(height: AppSpacing.sm),
            AppButton(
              variant: AppButtonVariant.secondary,
              onPressed: () =>
                  Navigator.pop(context, PhotoReviewDecision.retake),
              icon: Icons.camera_alt_outlined,
              label: 'Repetir foto',
            ),
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancelar'),
            ),
            const Text(
              'Confirmar la foto no la envia. El procesamiento se inicia despues, desde la pantalla del documento.',
            ),
          ],
        ),
      ),
    ),
  );
}
