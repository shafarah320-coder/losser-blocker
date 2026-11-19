# Screen Censor 2.0

Targets all detected faces and NudeNet's FEMALE_BREAST_EXPOSED class. It does not attempt to infer gender from faces.

## Build
Push these files to the GitHub repository's `main` branch, then run Actions > Build Windows Installer. Download artifact `ScreenCensor-Windows-Installer-v2`.

## Safety / limitations
- The overlay is hidden synchronously through Win32 during screen capture to avoid capturing itself.
- Ctrl+Shift+F12 is an emergency stop shortcut.
- Detection is periodic (~1 second), probabilistic, and can miss content or produce false positives.
- NudeNet may download its model on first launch; internet access may be needed.
- The installer is unsigned. Scan it with Microsoft Defender before running.
- This is a new build and has not been tested on the user's PC. Test first with non-sensitive content and keep Task Manager available.
