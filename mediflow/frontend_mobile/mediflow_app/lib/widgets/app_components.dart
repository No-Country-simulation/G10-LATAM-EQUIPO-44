import 'package:flutter/material.dart';
import '../design_system/app_colors.dart';
import '../design_system/app_spacing.dart';

// Agregado por Edil: componentes exclusivamente visuales, con controles Material accesibles.
enum AppButtonVariant { primary, secondary, text }

class AppButton extends StatelessWidget {
  const AppButton({
    super.key,
    required this.label,
    required this.icon,
    required this.onPressed,
    this.variant = AppButtonVariant.primary,
  });
  final String label;
  final IconData icon;
  final VoidCallback? onPressed;
  final AppButtonVariant variant;
  @override
  Widget build(BuildContext context) {
    final text = Text(label, textAlign: TextAlign.center);
    return switch (variant) {
      AppButtonVariant.primary => FilledButton.icon(
        onPressed: onPressed,
        icon: Icon(icon),
        label: text,
      ),
      AppButtonVariant.secondary => OutlinedButton.icon(
        onPressed: onPressed,
        icon: Icon(icon),
        label: text,
      ),
      AppButtonVariant.text => TextButton.icon(
        onPressed: onPressed,
        icon: Icon(icon),
        label: text,
      ),
    };
  }
}

class AppCard extends StatelessWidget {
  const AppCard({super.key, required this.child, this.padding = AppSpacing.xl});
  final Widget child;
  final double padding;
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(padding: EdgeInsets.all(padding), child: child),
  );
}

class AppHeader extends StatelessWidget {
  const AppHeader({
    super.key,
    required this.title,
    required this.subtitle,
    this.eyebrow,
  });
  final String title;
  final String subtitle;
  final String? eyebrow;
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      if (eyebrow != null) ...[
        Text(
          eyebrow!,
          style: Theme.of(
            context,
          ).textTheme.labelLarge?.copyWith(color: AppColors.primary),
        ),
        const SizedBox(height: AppSpacing.sm),
      ],
      Semantics(
        header: true,
        child: Text(title, style: Theme.of(context).textTheme.headlineSmall),
      ),
      const SizedBox(height: AppSpacing.md),
      Text(
        subtitle,
        style: Theme.of(
          context,
        ).textTheme.bodyLarge?.copyWith(color: AppColors.secondaryText),
      ),
    ],
  );
}

enum AppStatusTone { information, success, warning, error }

class AppStatusPanel extends StatelessWidget {
  const AppStatusPanel({
    super.key,
    required this.title,
    this.message,
    this.tone = AppStatusTone.information,
    this.loading = false,
  });
  final String title;
  final String? message;
  final AppStatusTone tone;
  final bool loading;
  @override
  Widget build(BuildContext context) {
    // Agregado por Edil: violeta distingue espera de éxito, revisión y error.
    final (color, background, icon) = loading
        ? (
            AppColors.secondary,
            AppColors.secondarySoft,
            Icons.hourglass_top_rounded,
          )
        : switch (tone) {
            AppStatusTone.information => (
              AppColors.primary,
              AppColors.primarySoft,
              Icons.info_outline,
            ),
            AppStatusTone.success => (
              AppColors.successForeground,
              AppColors.successSoft,
              Icons.check_circle_outline,
            ),
            AppStatusTone.warning => (
              AppColors.warning,
              AppColors.warningSoft,
              Icons.person_search_outlined,
            ),
            AppStatusTone.error => (
              AppColors.error,
              AppColors.errorSoft,
              Icons.warning_amber_rounded,
            ),
          };
    return Semantics(
      liveRegion: true,
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.lg),
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(AppSpacing.radiusSm),
          border: Border.all(color: color.withValues(alpha: .25)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (loading)
              SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(
                  strokeWidth: 2.5,
                  color: color,
                ),
              )
            else
              Icon(icon, color: color),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: AppColors.clinicalBlue,
                    ),
                  ),
                  if (message != null) ...[
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      message!,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
