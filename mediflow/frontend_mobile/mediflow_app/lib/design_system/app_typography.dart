import 'package:flutter/material.dart';
import 'app_colors.dart';

// Agregado por Edil: Roboto compatible con Flutter; no descarga fuentes ni agrega dependencias.
abstract final class AppTypography {
  static const family = 'Roboto';
  static const textTheme = TextTheme(
    headlineMedium: TextStyle(
      fontSize: 28,
      height: 1.25,
      fontWeight: FontWeight.w700,
    ),
    headlineSmall: TextStyle(
      fontSize: 24,
      height: 1.3,
      fontWeight: FontWeight.w700,
    ),
    titleLarge: TextStyle(
      fontSize: 20,
      height: 1.35,
      fontWeight: FontWeight.w600,
    ),
    titleMedium: TextStyle(
      fontSize: 17,
      height: 1.4,
      fontWeight: FontWeight.w600,
    ),
    bodyLarge: TextStyle(fontSize: 16, height: 1.5),
    bodyMedium: TextStyle(fontSize: 14, height: 1.5),
    bodySmall: TextStyle(
      fontSize: 12,
      height: 1.5,
      color: AppColors.secondaryText,
    ),
    labelLarge: TextStyle(
      fontSize: 14,
      height: 1.3,
      fontWeight: FontWeight.w600,
    ),
  );
}
