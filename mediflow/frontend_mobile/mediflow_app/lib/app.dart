import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'screens/home_screen.dart';
import 'design_system/app_theme.dart';
import 'services/file_picker_service.dart';
import 'services/document_camera_service.dart';
import 'services/triage_api_service.dart';

class MediFlowApp extends StatelessWidget {
  const MediFlowApp({
    super.key,
    this.filePickerService,
    this.triageApiService,
    this.cameraService,
  });

  final FilePickerService? filePickerService;
  final TriageApiService? triageApiService;
  final DocumentCameraService? cameraService;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MediFlow',
      debugShowCheckedModeBanner: false,
      locale: const Locale('es'),
      supportedLocales: const [Locale('es')],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      theme: AppTheme.light,
      home: HomeScreen(
        filePickerService: filePickerService,
        triageApiService: triageApiService,
        cameraService: cameraService,
      ),
    );
  }
}
