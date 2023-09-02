import importlib
import inspect
import os
import sys

from mporg.plugins import FINGERPRINTER_DIR, PLUGIN_DIR
from mporg.plugins.util import PluginType, Plugin


def get_class_by_pattern(module, pattern):
    classes = inspect.getmembers(module, inspect.isclass)
    matching = [cls for cls_name, cls in classes if pattern in cls_name]
    return matching


class PluginLoader:
    def __init__(self):
        self.plugins = {}
        self.cred_managers = {}
        self.fingerprinters = {}

    def fingerprinter_from_file(self, file: str):
        plugin_name = file.replace("Plugin.py", "")
        module_name = plugin_name + "Plugin"

        try:
            spec = importlib.util.spec_from_file_location(module_name, FINGERPRINTER_DIR / file)
            # module = SourceFileLoader(module_name, FINGERPRINTER_DIR / file).load_module()
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            fingerprinter = getattr(module, plugin_name)
            cred = get_class_by_pattern(module, "CredentialProvider")[0]

            self.fingerprinters[plugin_name] = Plugin(fingerprinter, cred)
        except (ModuleNotFoundError, AttributeError) as e:
            print(e)

    def load_plugin(self, plugin_type: PluginType, plugin_name: str):
        if FINGERPRINTER_DIR.exists():
            print(FINGERPRINTER_DIR)

        fingerprinter_files = [f for f in os.listdir(PLUGIN_DIR / plugin_type.value) if f.endswith("Plugin.py")]
        fil_name = plugin_name.lower().strip()
        file = [f for f in fingerprinter_files if fil_name in f.lower().strip()][0]

        self.fingerprinter_from_file(file)

    def load_all_fingerprinters(self):
        if FINGERPRINTER_DIR.exists():
            print(FINGERPRINTER_DIR)

        fingerprinter_files = [f for f in os.listdir(FINGERPRINTER_DIR) if f.endswith("Plugin.py")]
        for file in fingerprinter_files:
            self.fingerprinter_from_file(file)

        print(self.fingerprinters)


if __name__ == "__main__":
    loader = PluginLoader()
    loader.load_plugin(PluginType.FINGERPRINTER, "MB")
    print(loader.fingerprinters)
