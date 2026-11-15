#!/usr/bin/env python3
"""
Clase base para todos los consolidadores.
Proporciona métodos compartidos y lógica común.
"""

import os
from abc import ABC, abstractmethod
from typing import List, Optional


class BaseConsolidator(ABC):
    """Clase base abstracta para todos los consolidadores."""
    
    def __init__(self, directory: str = "."):
        """
        Inicializa el consolidador.
        
        Args:
            directory: Directorio de trabajo donde buscar archivos
        """
        self.directory = directory
    
    def confirm_deletion(self, files: List[str], file_type: str = "archivo") -> bool:
        """
        Solicita confirmación para borrar archivos.
        
        Args:
            files: Lista de rutas de archivos a borrar
            file_type: Tipo de archivo (para mensaje descriptivo)
        
        Returns:
            True si el usuario confirma, False en caso contrario
        """
        if not files:
            return False
        
        print(f"\n📋 Se borrarán {len(files)} {file_type}(s):")
        for f in files:
            print(f"  - {os.path.basename(f)}")
        
        return self._confirm_yes_no("\n⚠️  ¿Confirmar borrado?")
    
    def handle_existing_output(self, output_filename: str) -> str:
        """
        Maneja el caso de que el archivo consolidado ya exista.
        
        Args:
            output_filename: Nombre del archivo que ya existe
        
        Returns:
            'regenerate' - Regenerar el consolidado
            'delete_only' - Solo borrar archivos origen
            'cancel' - Cancelar operación
        """
        print(f"\n⚠️  El archivo consolidado ya existe: {output_filename}")
        print("\nOpciones:")
        print("  1. Regenerar el consolidado")
        print("  2. Solo borrar archivos origen (mantener consolidado actual)")
        print("  3. Cancelar")
        
        choice = input("\nSelecciona una opción (1/2/3): ").strip()
        
        if choice == '1':
            return 'regenerate'
        elif choice == '2':
            return 'delete_only'
        else:
            return 'cancel'
    
    def delete_files_confirmed(self, files: List[str]) -> int:
        """
        Borra archivos después de que el usuario haya confirmado.
        
        Args:
            files: Lista de rutas de archivos a borrar
        
        Returns:
            Número de archivos borrados exitosamente
        """
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
    
    @staticmethod
    def _confirm_yes_no(prompt: str) -> bool:
        """
        Solicita confirmación de sí/no.
        
        Args:
            prompt: Mensaje a mostrar
        
        Returns:
            True si responde sí, False en caso contrario
        """
        response = input(f"{prompt} (s/N): ").strip().lower()
        return response in ['s', 'si', 'sí', 'y', 'yes']
    
    @staticmethod
    def adjust_markdown_headings(content: str, skip_first_line: bool = True) -> str:
        """
        Ajusta niveles de encabezados Markdown (agrega un # al inicio).
        
        Args:
            content: Contenido a procesar
            skip_first_line: Si True, omite la primera línea (título)
        
        Returns:
            Contenido con encabezados ajustados
        """
        lines = content.split('\n')
        start_idx = 1 if skip_first_line else 0
        adjusted_lines = []
        
        for i, line in enumerate(lines):
            if i < start_idx:
                continue
            
            if line.startswith('#'):
                adjusted_lines.append('#' + line)
            else:
                adjusted_lines.append(line)
        
        return '\n'.join(adjusted_lines)
    
    @staticmethod
    def remove_markdown_metadata(content: str) -> str:
        """
        Elimina líneas de metadata de archivos consolidados (>, ---).
        
        Args:
            content: Contenido a procesar
        
        Returns:
            Contenido sin metadata
        """
        lines = content.split('\n')
        cleaned = []
        skip_metadata = True
        
        for line in lines[1:]:  # Skip first line (title)
            if skip_metadata and (line.startswith('>') or 
                                 line.startswith('---') or
                                 line.strip() == ''):
                continue
            skip_metadata = False
            cleaned.append(line)
        
        # Limpiar líneas vacías al inicio
        while cleaned and cleaned[0].strip() == '':
            cleaned.pop(0)
        
        return '\n'.join(cleaned)
    
    @abstractmethod
    def consolidate(self, *args, **kwargs) -> bool:
        """
        Método abstracto que deben implementar las subclases.
        
        Returns:
            True si la consolidación fue exitosa, False en caso contrario
        """
        pass
