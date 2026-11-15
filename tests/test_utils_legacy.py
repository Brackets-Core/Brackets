#!/usr/bin/env python3
"""
Tests unitarios para funciones en utils/legacy_utils.py
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.legacy_utils import (
    get_season_emoji,
    get_work_location,
    safe_file_read,
    safe_file_write,
    confirm_overwrite,
    parse_float_input,
    calculate_next_week_info_from_dates,
    generate_filename
)


class TestLegacyUtils:
    """Tests para funciones en legacy_utils.py"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
    
    def test_get_season_emoji(self):
        """Test que get_season_emoji devuelve emojis correctos."""
        try:
            assert get_season_emoji(1) == "❄️", "Enero debería ser invierno"
            assert get_season_emoji(4) == "🌱", "Abril debería ser primavera"
            assert get_season_emoji(7) == "☀️", "Julio debería ser verano"
            assert get_season_emoji(10) == "🍂", "Octubre debería ser otoño"
            
            print("✅ Test: get_season_emoji devuelve emojis correctos")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test get_season_emoji falló: {e}")
            self.failed += 1
    
    def test_get_work_location(self):
        """Test que get_work_location devuelve ubicaciones correctas."""
        try:
            # Monday (0) - Casa
            assert get_work_location(0) == "🏠", "Lunes debería ser casa"
            # Tuesday (1) - Oficina
            assert get_work_location(1) == "🚗", "Martes debería ser oficina"
            # Friday (4) - Alternante
            location_even = get_work_location(4, week_number=2)
            location_odd = get_work_location(4, week_number=3)
            assert location_even == "🏠", "Viernes semana par debería ser casa"
            assert location_odd == "🚗", "Viernes semana impar debería ser oficina"
            
            print("✅ Test: get_work_location devuelve ubicaciones correctas")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test get_work_location falló: {e}")
            self.failed += 1
    
    def test_safe_file_read_write(self):
        """Test que safe_file_read/write funcionan correctamente."""
        try:
            import tempfile
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                temp_path = f.name
                test_content = "Contenido de prueba 📝"
            
            try:
                # Escribir
                result = safe_file_write(temp_path, test_content)
                assert result == True, "safe_file_write debería retornar True"
                
                # Leer
                content = safe_file_read(temp_path)
                assert content == test_content, f"Contenido no coincide: {content}"
                
                print("✅ Test: safe_file_read/write funcionan correctamente")
                self.passed += 1
            finally:
                os.unlink(temp_path)
        except Exception as e:
            print(f"❌ Test safe_file_read_write falló: {e}")
            self.failed += 1
    
    def test_parse_float_input(self):
        """Test que parse_float_input convierte correctamente."""
        try:
            assert parse_float_input("75.5") == 75.5, "Debería parsear decimal"
            assert parse_float_input("80") == 80.0, "Debería parsear entero"
            assert parse_float_input("") is None, "String vacío debería retornar None"
            assert parse_float_input("", default=70.0) == 70.0, "Debería usar default"
            assert parse_float_input("invalid") is None, "String inválido debería retornar None"
            
            print("✅ Test: parse_float_input convierte correctamente")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test parse_float_input falló: {e}")
            self.failed += 1
    
    def test_calculate_next_week_info_from_dates(self):
        """Test que calculate_next_week_info_from_dates calcula correctamente."""
        try:
            from datetime import datetime
            # Semana normal: fechas de semana 5 -> debe devolver semana 6
            dates = [datetime(2026, 2, 2 + i) for i in range(5)]  # Lun-Vie
            year, month, week = calculate_next_week_info_from_dates(dates, 5)
            assert week == 6, f"Semana siguiente debería ser 6, se obtuvo {week}"
            assert year == 2026
            assert month == 2
            
            # Cambio de año: semana 52 -> semana 1
            dates52 = [datetime(2026, 12, 21 + i) for i in range(5)]  # Lun 21-Vie 25 Dec
            year2, month2, week2 = calculate_next_week_info_from_dates(dates52, 52)
            assert week2 == 1, f"Semana 53 debería cambiar a 1, se obtuvo {week2}"
            
            print("✅ Test: calculate_next_week_info_from_dates calcula correctamente")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test calculate_next_week_info_from_dates falló: {e}")
            self.failed += 1
    
    def test_generate_filename(self):
        """Test que generate_filename genera nombres correctos."""
        try:
            # Archivo semanal
            weekly = generate_filename(2026, 1, week=5)
            assert "[2026][01]Week05.md" in weekly, f"Nombre semanal incorrecto: {weekly}"
            
            # Archivo mensual
            monthly = generate_filename(2026, 1, is_monthly=True)
            assert "[2026][01]MonthTopics.md" in monthly, f"Nombre mensual incorrecto: {monthly}"
            
            print("✅ Test: generate_filename genera nombres correctos")
            self.passed += 1
        except Exception as e:
            print(f"❌ Test generate_filename falló: {e}")
            self.failed += 1
    
    def run_all(self):
        """Ejecutar todos los tests."""
        print("\n🧪 TESTS: utils/legacy_utils.py")
        print("=" * 50)
        
        self.test_get_season_emoji()
        self.test_get_work_location()
        self.test_safe_file_read_write()
        self.test_parse_float_input()
        self.test_calculate_next_week_info_from_dates()
        self.test_generate_filename()
        
        print(f"\n📊 Resultado: ✅ {self.passed} | ❌ {self.failed}")
        return self.failed == 0


if __name__ == "__main__":
    tester = TestLegacyUtils()
    success = tester.run_all()
    sys.exit(0 if success else 1)
