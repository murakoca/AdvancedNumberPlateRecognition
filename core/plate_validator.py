"""
Türkiye Plaka Validator
"""
import re

class TRPlateValidator:
    """Türkiye Plaka Kuralları Validator"""
    
    CITY_CODES = set(f"{i:02d}" for i in range(1, 82))
    INVALID_LETTERS = set(['Ç', 'Ğ', 'İ', 'Ö', 'Ü', 'Ş'])
    
    @staticmethod
    def clean_plate(text):
        if not text:
            return ""
        return re.sub(r'[^A-Z0-9]', '', text.upper())
    
    @staticmethod
    def is_valid_city_code(code):
        return code in TRPlateValidator.CITY_CODES
    
    @staticmethod
    def is_valid_letter_group(letters):
        if not letters or len(letters) < 1 or len(letters) > 3:
            return False
        for letter in letters:
            if letter in TRPlateValidator.INVALID_LETTERS:
                return False
            if not letter.isalpha():
                return False
        return True
    
    @staticmethod
    def is_valid_number_group(numbers):
        if not numbers or len(numbers) < 2 or len(numbers) > 4:
            return False
        return numbers.isdigit()
    
    @staticmethod
    def validate_full_plate(plate_text):
        cleaned = TRPlateValidator.clean_plate(plate_text)
        
        if len(cleaned) < 7 or len(cleaned) > 9:
            return False, f"Geçersiz uzunluk: {len(cleaned)}"
        
        city_code = cleaned[:2]
        if not city_code.isdigit():
            return False, f"İl kodu rakam olmalı: {city_code}"
        
        if not TRPlateValidator.is_valid_city_code(city_code):
            return False, f"Geçersiz il kodu: {city_code}"
        
        remaining = cleaned[2:]
        letters = ""
        numbers = ""
        
        for char in remaining:
            if char.isalpha():
                letters += char
            elif char.isdigit():
                numbers += char
            else:
                return False, f"Geçersiz karakter: {char}"
        
        if len(letters) < 1 or len(letters) > 3:
            return False, f"Harf grubu 1-3 karakter olmalı: {letters}"
        
        for letter in letters:
            if letter in TRPlateValidator.INVALID_LETTERS:
                return False, f"Geçersiz harf: {letter}"
        
        if len(numbers) < 2 or len(numbers) > 4:
            return False, f"Sayı grubu 2-4 karakter olmalı: {numbers}"
        
        formatted = f"{city_code}{letters}{numbers}"
        if formatted != cleaned:
            return False, f"Format hatası: {cleaned} -> {formatted}"
        
        return True, formatted
    
    @staticmethod
    def format_plate(plate_text):
        cleaned = TRPlateValidator.clean_plate(plate_text)
        valid, result = TRPlateValidator.validate_full_plate(cleaned)
        
        if valid:
            city = result[:2]
            remaining = result[2:]
            
            letters = ""
            numbers = ""
            for char in remaining:
                if char.isalpha():
                    letters += char
                else:
                    numbers += char
            
            return f"{city} {letters} {numbers}"
        return plate_text

# Yardımcı fonksiyonlar
def is_valid_tr_plate(text):
    valid, _ = TRPlateValidator.validate_full_plate(text)
    return valid

def format_tr_plate(text):
    return TRPlateValidator.format_plate(text)