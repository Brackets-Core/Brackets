#!/usr/bin/env python3
"""
Funciones auxiliares compartidas por todos los módulos.
"""

import os
from typing import List


def confirm_yes_no(prompt: str) -> bool:
    """
    Solicita confirmación de sí/no al usuario.
    
    Args:
        prompt: Mensaje a mostrar
    
    Returns:
        True si responde afirmativamente, False en caso contrario
    """
    response = input(f"{prompt} (s/N): ").strip().lower()
    return response in ['s', 'si', 'sí', 'y', 'yes']


def list_files_for_deletion(files: List[str]) -> None:
    """
    Muestra una lista de archivos que serán borrados.
    
    Args:
        files: Lista de rutas de archivos
    """
    for f in files:
        print(f"  - {os.path.basename(f)}")


def delete_files(files: List[str], confirm: bool = True) -> int:
    """
    Borra archivos con confirmación opcional.
    
    Args:
        files: Lista de rutas de archivos a borrar
        confirm: Si True, solicita confirmación antes de borrar
    
    Returns:
        Número de archivos borrados exitosamente
    """
    if confirm:
        print(f"\n📋 Se borrarán {len(files)} archivo(s):")
        list_files_for_deletion(files)
        
        if not confirm_yes_no("\n⚠️  ¿Confirmar borrado?"):
            print("\n↩️  Operación de borrado cancelada")
            return 0
    
    deleted = 0
    for filepath in files:
        try:
            os.remove(filepath)
            deleted += 1
            print(f"  ✅ Borrado: {os.path.basename(filepath)}")
        except Exception as e:
            print(f"  ❌ Error al borrar {os.path.basename(filepath)}: {e}")
    
    print(f"\n🗑️  {deleted} archivo(s) borrado(s)")
    return deleted


def get_file_size_mb(filepath: str) -> float:
    """
    Obtiene el tamaño de un archivo en MB.
    
    Args:
        filepath: Ruta al archivo
    
    Returns:
        Tamaño en MB
    """
    try:
        size_bytes = os.path.getsize(filepath)
        return size_bytes / (1024 * 1024)
    except Exception:
        return 0.0
