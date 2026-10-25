import 'package:flutter/material.dart';
import 'app_colors.dart';
import 'app_spacing.dart';
import 'app_typography.dart';

abstract final class AppTheme {
  static ThemeData get light {
    final colors = ColorScheme.fromSeed(seedColor: AppColors.primary).copyWith(
      primary: AppColors.primary,
      onPrimary: Colors.white,
      primaryContainer: AppColors.primarySoft,
      onPrimaryContainer: AppColors.clinicalBlue,
      secondary: AppColors.secondary,
      onSecondary: Colors.white,
      secondaryContainer: AppColors.secondarySoft,
      onSecondaryContainer: AppColors.secondary,
      surface: AppColors.card,
      onSurface: AppColors.clinicalBlue,
      onSurfaceVariant: AppColors.secondaryText,
      error: AppColors.error,
      onError: Colors.white,
      errorContainer: AppColors.errorSoft,
      onErrorContainer: AppColors.error,
      outline: AppColors.secondaryText,
      outlineVariant: AppColors.outline,
    );
    final shape = RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(AppSpacing.radiusSm),
    );
    final button = ButtonStyle(
      minimumSize: const WidgetStatePropertyAll(Size(48, 52)),
      padding: const WidgetStatePropertyAll(
        EdgeInsets.symmetric(
          horizontal: AppSpacing.lg,
          vertical: AppSpacing.md,
        ),
      ),
      shape: WidgetStatePropertyAll(shape),
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: colors,
      fontFamily: AppTypography.family,
      scaffoldBackgroundColor: AppColors.background,
      textTheme: AppTypography.textTheme.apply(
        bodyColor: AppColors.clinicalBlue,
        displayColor: AppColors.clinicalBlue,
        fontFamily: AppTypography.family,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.background,
        foregroundColor: AppColors.clinicalBlue,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: AppColors.card,
        surfaceTintColor: Colors.transparent,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppSpacing.radiusLg),
          side: const BorderSide(color: AppColors.outline),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(style: button),
      outlinedButtonTheme: OutlinedButtonThemeData(style: button),
      textButtonTheme: TextButtonThemeData(style: button),
      chipTheme: ChipThemeData(
        backgroundColor: AppColors.primarySoft,
        side: BorderSide.none,
        shape: shape,
        labelStyle: const TextStyle(
          fontFamily: AppTypography.family,
          color: AppColors.clinicalBlue,
          fontWeight: FontWeight.w500,
        ),
      ),
      // Agregado por Edil: coherencia visual de foco, consentimiento e iconos.
      focusColor: AppColors.primarySoft,
      iconTheme: const IconThemeData(color: AppColors.primary, size: 24),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.card,
        contentPadding: const EdgeInsets.all(AppSpacing.lg),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppSpacing.radiusSm),
          borderSide: const BorderSide(color: AppColors.outline),
        ),
      ),
      checkboxTheme: CheckboxThemeData(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppSpacing.xs),
        ),
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: AppColors.primary,
      ),
      dividerTheme: const DividerThemeData(color: AppColors.outline),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: AppColors.clinicalBlue,
        shape: shape,
      ),
    );
  }
}
