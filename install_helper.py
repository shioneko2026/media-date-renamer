"""
install_helper.py — Register or unregister MediaRenamer context menu entries.

Usage:
    python install_helper.py --install   [--elevate]
    python install_helper.py --uninstall [--elevate]

--elevate: if not already running as admin, re-launch self with UAC elevation.
"""

import sys
import os
import ctypes
import argparse

# Always resolve paths relative to this file's directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Legacy key names from the old install.bat (cleaned up on install)
LEGACY_KEYS = [
    ('Directory\\Background\\shell', 'RenameMediaFiles'),
    ('Directory\\shell', 'UpdateFolderToday'),
    ('Directory\\shell', 'UpdateFolderLatest'),
]


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def elevate_and_relaunch():
    """Re-launch this script with admin rights via UAC. Parent process exits."""
    script = os.path.abspath(__file__)
    args = ' '.join(f'"{a}"' for a in sys.argv[1:] if a != '--elevate')
    # ShellExecuteW: runas = request elevation
    ret = ctypes.windll.shell32.ShellExecuteW(
        None, 'runas', sys.executable, f'"{script}" {args}', None, 1
    )
    if ret <= 32:
        print(f'ERROR: Could not elevate (ShellExecuteW returned {ret}).')
        sys.exit(1)
    sys.exit(0)


def resolve_pythonw() -> str:
    """Return the pythonw.exe path next to the current python.exe."""
    candidate = sys.executable.replace('python.exe', 'pythonw.exe')
    if os.path.isfile(candidate):
        return candidate
    return 'pythonw.exe'  # Fall back to PATH lookup


def load_config() -> dict:
    sys.path.insert(0, SCRIPT_DIR)
    from core.config import load_config as _load
    return _load()


def _delete_key_tree(winreg, root, subkey: str):
    """Delete a registry key and all its subkeys (recursive)."""
    import winreg as wr
    try:
        # Delete children first
        key = wr.OpenKey(root, subkey, 0, wr.KEY_ALL_ACCESS)
        while True:
            try:
                child = wr.EnumKey(key, 0)
                _delete_key_tree(wr, root, f'{subkey}\\{child}')
            except OSError:
                break
        wr.CloseKey(key)
        wr.DeleteKey(root, subkey)
    except FileNotFoundError:
        pass


def install(config: dict):
    import winreg

    pythonw = resolve_pythonw()
    items = sorted(
        config.get('context_menu', {}).get('items', []),
        key=lambda x: x.get('sort_order', 99)
    )

    # ── Clean up legacy keys ──────────────────────────────────────────────────
    for parent, key_name in LEGACY_KEYS:
        _delete_key_tree(winreg, winreg.HKEY_CLASSES_ROOT, f'{parent}\\{key_name}')

    # ── Also clean up any existing MediaRenamer keys (in case of re-install) ──
    for item in items:
        item_id = item.get('id', '')
        trigger = item.get('trigger', 'background')
        parent = _trigger_to_parent(trigger)
        # Remove all keys that might match our naming pattern for this item
        for order in range(1, 20):
            old_key = f'{parent}\\{order:02d}_{_sanitize_id(item_id)}'
            _delete_key_tree(winreg, winreg.HKEY_CLASSES_ROOT, old_key)

    # ── Write new entries ─────────────────────────────────────────────────────
    for item in items:
        if not item.get('enabled', True):
            continue

        item_id = item.get('id', '')
        label = item.get('label', item_id)
        icon_rel = item.get('icon', '')
        trigger = item.get('trigger', 'background')
        script = item.get('script', '')
        position = item.get('position', 'bottom')
        sort_order = item.get('sort_order', 99)

        # Absolute paths
        script_path = os.path.join(SCRIPT_DIR, script)
        icon_path = os.path.join(SCRIPT_DIR, icon_rel) if icon_rel else ''

        parent = _trigger_to_parent(trigger)
        key_name = f'{sort_order:02d}_{_sanitize_id(item_id)}'
        full_key = f'{parent}\\{key_name}'

        # Command uses %V (background) or %1 (directory)
        param = '%V' if trigger == 'background' else '%1'
        command = f'"{pythonw}" "{script_path}" "{param}"'

        # Write main key
        with winreg.CreateKeyEx(winreg.HKEY_CLASSES_ROOT, full_key,
                                0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, '', 0, winreg.REG_SZ, label)
            if icon_path and os.path.isfile(icon_path):
                winreg.SetValueEx(k, 'Icon', 0, winreg.REG_SZ, icon_path)
            elif icon_path:
                # Icon file missing — skip silently
                pass
            winreg.SetValueEx(k, 'Position', 0, winreg.REG_SZ,
                              'Top' if position == 'top' else 'Bottom')

        # Write command subkey
        with winreg.CreateKeyEx(winreg.HKEY_CLASSES_ROOT, f'{full_key}\\command',
                                0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, '', 0, winreg.REG_SZ, command)

        print(f'[OK] Registered: {label!r} → {full_key}')

    print('\nMediaRenamer context menu installed successfully.')


def uninstall(config: dict):
    import winreg

    items = config.get('context_menu', {}).get('items', [])

    # Remove new-style keys
    for item in items:
        item_id = item.get('id', '')
        trigger = item.get('trigger', 'background')
        parent = _trigger_to_parent(trigger)
        for order in range(1, 20):
            key = f'{parent}\\{order:02d}_{_sanitize_id(item_id)}'
            _delete_key_tree(winreg, winreg.HKEY_CLASSES_ROOT, key)

    # Remove legacy keys
    for parent, key_name in LEGACY_KEYS:
        _delete_key_tree(winreg, winreg.HKEY_CLASSES_ROOT, f'{parent}\\{key_name}')

    print('MediaRenamer context menu uninstalled.')


def _trigger_to_parent(trigger: str) -> str:
    if trigger == 'background':
        return 'Directory\\Background\\shell'
    return 'Directory\\shell'


def _sanitize_id(item_id: str) -> str:
    """Remove underscores and lowercase for use in key name."""
    return item_id.replace('_', '').lower()


def main():
    parser = argparse.ArgumentParser(description='MediaRenamer context menu installer')
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--uninstall', action='store_true')
    parser.add_argument('--elevate', action='store_true',
                        help='Request UAC elevation if not already admin')
    args = parser.parse_args()

    if not args.install and not args.uninstall:
        parser.print_help()
        sys.exit(1)

    if args.elevate and not is_admin():
        elevate_and_relaunch()

    config = load_config()

    if args.install:
        install(config)
    elif args.uninstall:
        uninstall(config)


if __name__ == '__main__':
    main()
