"""
Utilidades compartidas por los tests.

Los archivos NodoC.py / NodoD.py se repiten (con distinto contenido) en
varias carpetas de Hits. Si se importaran con `import NodoC` a secas,
Python los cachearía en sys.modules por nombre y el segundo import
devolvería el módulo del primer Hit en vez de recargar el archivo correcto.

`load_module` carga cada archivo como un módulo aislado, con un nombre
único generado con uuid, de forma que:
- cada test puede importar, por ejemplo, tanto hit6/NodoD.py como
  hit7/NodoD.py sin que se pisen entre sí.
- cada llamada a `load_module` para el mismo archivo devuelve una
  instancia *nueva* del módulo, con su propio estado global reiniciado
  (listas en RAM vacías, etc.), lo cual es clave para no arrastrar estado
  de un test a otro.
"""

import importlib.util
import pathlib
import sys
import uuid

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_module(relative_path: str):
    """Carga `relative_path` (ej: "hit6/NodoD.py") como módulo aislado."""
    file_path = REPO_ROOT / relative_path

    # hit8/NodoC.py hace `import nodos_pb2` / `import nodos_pb2_grpc` de forma
    # absoluta (no relativa), así que su carpeta debe estar en sys.path para
    # que esos imports funcionen al cargar el módulo.
    parent_dir = str(file_path.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    module_name = "_test_{}_{}".format(
        relative_path.replace("/", "_").replace(".", "_"),
        uuid.uuid4().hex[:8],
    )
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
