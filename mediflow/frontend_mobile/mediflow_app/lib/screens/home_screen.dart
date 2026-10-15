import 'package:flutter/material.dart';
import '../services/file_picker_service.dart';
import '../services/document_camera_service.dart';
import '../services/triage_api_service.dart';
import '../design_system/app_colors.dart';
import '../design_system/app_spacing.dart';
import '../widgets/app_components.dart';
import 'document_selection_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({
    super.key,
    this.filePickerService,
    this.triageApiService,
    this.cameraService,
  });
  final FilePickerService? filePickerService;
  final TriageApiService? triageApiService;
  final DocumentCameraService? cameraService;
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('MediFlow')),
    body: SafeArea(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: AppSpacing.contentWidth),
          child: ListView(
            padding: EdgeInsets.all(
              MediaQuery.sizeOf(context).width < 400
                  ? AppSpacing.lg
                  : AppSpacing.xl,
            ),
            children: [
              const SizedBox(height: AppSpacing.lg),
              Align(
                alignment: Alignment.centerLeft,
                child: Container(
                  padding: const EdgeInsets.all(AppSpacing.lg),
                  decoration: BoxDecoration(
                    color: AppColors.primarySoft,
                    borderRadius: BorderRadius.circular(AppSpacing.radiusLg),
                  ),
                  child: const Icon(
                    Icons.health_and_safety_outlined,
                    size: 40,
                    color: AppColors.primary,
                  ),
                ),
              ),
              const SizedBox(height: AppSpacing.xl),
              const AppHeader(
                eyebrow: 'DOCUMENTOS CLÍNICOS',
                title: 'Triaje de documentos clínicos',
                subtitle:
                    'Organiza el ingreso de tus documentos y consulta la respuesta del servidor.',
              ),
              const SizedBox(height: AppSpacing.xxl),
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Documentos admitidos',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    const Wrap(
                      spacing: AppSpacing.sm,
                      runSpacing: AppSpacing.sm,
                      children: [
                        Chip(
                          avatar: Icon(Icons.picture_as_pdf_outlined),
                          label: Text('PDF'),
                        ),
                        Chip(
                          avatar: Icon(Icons.image_outlined),
                          label: Text('Imagen'),
                        ),
                        Chip(
                          avatar: Icon(Icons.description_outlined),
                          label: Text('Texto'),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),
                    const Text('PDF, JPG, JPEG, PNG y TXT'),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.xl),
              AppButton(
                label: 'Seleccionar documento',
                icon: Icons.add_rounded,
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => DocumentSelectionScreen(
                      filePickerService: filePickerService,
                      triageApiService: triageApiService,
                      cameraService: cameraService,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: AppSpacing.xl),
              const AppStatusPanel(
                title: 'Tú decides cuándo enviar',
                message:
                    'Selecciona un archivo local. Solo se enviará al servidor cuando pulses Procesar documento.',
              ),
              const SizedBox(height: AppSpacing.lg),
            ],
          ),
        ),
      ),
    ),
  );
}
