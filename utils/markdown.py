#!/usr/bin/env python3
"""
Utilidades para procesamiento de archivos Markdown.
"""

from typing import List


def adjust_headings(content: str, level: int = 1, skip_first_line: bool = True) -> str:
    """
    Aumenta el nivel de todos los encabezados Markdown.
    
    Args:
        content: Contenido Markdown a procesar
        level: Número de niveles a aumentar (número de # a agregar)
        skip_first_line: Si True, omite la primera línea (título principal)
    
    Returns:
        Contenido con encabezados ajustados
    
    Example:
        ## Título        ->  ### Título (si level=1)
        ### Subtítulo    ->  #### Subtítulo (si level=1)
    """
    lines = content.split('\n')
    start_idx = 1 if skip_first_line else 0
    adjusted = []
    
    for i, line in enumerate(lines):
        if i < start_idx:
            continue
        
        if line.startswith('#'):
            adjusted.append('#' * level + line)
        else:
            adjusted.append(line)
    
    return '\n'.join(adjusted)


def remove_metadata(content: str) -> str:
    """
    Elimina líneas de metadata de archivos consolidados.
    Remueve líneas que empiezan con '>' o '---' y líneas vacías iniciales.
    
    Args:
        content: Contenido Markdown a limpiar
    
    Returns:
        Contenido sin metadata
    
    Example:
        # Título
        > Metadata
        > Otra metadata
        ---
        
        Contenido real...
        
        ->
        
        Contenido real...
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


def extract_title(content: str) -> str:
    """
    Extrae el título (primera línea con #) de un archivo Markdown.
    
    Args:
        content: Contenido Markdown
    
    Returns:
        Título sin el símbolo #
    """
    lines = content.split('\n')
    for line in lines:
        if line.startswith('#'):
            return line.lstrip('#').strip()
    return ""


def count_headings(content: str) -> dict:
    """
    Cuenta encabezados por nivel en un archivo Markdown.
    
    Args:
        content: Contenido Markdown
    
    Returns:
        Diccionario con conteo {nivel: cantidad}
    """
    lines = content.split('\n')
    counts = {}
    
    for line in lines:
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            counts[level] = counts.get(level, 0) + 1
    
    return counts
