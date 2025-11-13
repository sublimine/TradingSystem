"""
ID Generation - IDs monotónicos para event sourcing y trazabilidad
Implementa UUIDv7 (time-ordered) y ULID para identificadores únicos ordenables.
"""

import time
import os
import random
from typing import Optional
from datetime import datetime


class IDGenerator:
    """
    Generador de IDs institucional con garantías de unicidad y ordenabilidad.
    
    Soporta:
    - UUIDv7: UUID con timestamp embebido (RFC draft)
    - ULID: Universally Unique Lexicographically Sortable Identifier
    - Batch IDs: Identificadores de batch de decisiones
    - Event IDs: Identificadores de eventos con chain linking
    """
    
    def __init__(self, node_id: Optional[int] = None):
        """
        Inicializa generador de IDs.
        
        Args:
            node_id: Identificador del nodo para distributed deployment (0-255)
        """
        self.node_id = node_id or (os.getpid() % 256)
        self._last_timestamp_ms = 0
        self._sequence = 0
        
    def generate_uuidv7(self) -> str:
        """
        Genera UUID versión 7 con timestamp embebido.
        
        UUIDv7 format (128 bits):
        - 48 bits: Unix timestamp in milliseconds
        - 12 bits: Sub-millisecond precision / sequence
        - 2 bits: Version (0b111 = 7)
        - 62 bits: Random data + node_id
        
        Returns:
            UUID v7 string en formato 8-4-4-4-12
        """
        # Obtener timestamp en milisegundos
        timestamp_ms = int(time.time() * 1000)
        
        # Manejar same-millisecond generation
        if timestamp_ms == self._last_timestamp_ms:
            self._sequence += 1
            if self._sequence >= 4096:  # 12 bits max
                # Wait for next millisecond
                while timestamp_ms == self._last_timestamp_ms:
                    time.sleep(0.001)
                    timestamp_ms = int(time.time() * 1000)
                self._sequence = 0
        else:
            self._sequence = 0
        
        self._last_timestamp_ms = timestamp_ms
        
        # Construir UUID v7
        # 48 bits timestamp
        time_high = (timestamp_ms >> 16) & 0xFFFFFFFF
        time_mid = (timestamp_ms >> 4) & 0xFFF
        time_low = (timestamp_ms & 0xF) << 12
        
        # 12 bits sequence + version
        time_low |= self._sequence
        
        # Version 7 (4 bits) = 0111
        version_clock = 0x7000 | (random.randint(0, 0xFFF))
        
        # 62 bits random + node_id
        random_high = random.randint(0, 0x3FFF)  # 14 bits
        random_low = (self.node_id << 40) | random.randint(0, 0xFFFFFFFFFF)  # 8 + 40 bits
        
        # Format as UUID string
        uuid_str = (
            f"{time_high:08x}-"
            f"{time_mid:04x}-"
            f"{version_clock:04x}-"
            f"{random_high:04x}-"
            f"{random_low:012x}"
        )
        
        return uuid_str.upper()
    
    def generate_ulid(self) -> str:
        """
        Genera ULID (Universally Unique Lexicographically Sortable Identifier).
        
        ULID format (128 bits, 26 characters base32):
        - 48 bits: Timestamp (milliseconds since epoch)
        - 80 bits: Random data
        
        Returns:
            ULID string (26 caracteres Crockford base32)
        """
        # Crockford base32 alphabet (sin I, L, O, U)
        ENCODING = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
        
        # Timestamp en milisegundos
        timestamp_ms = int(time.time() * 1000)
        
        # Generar 80 bits random
        random_bytes = os.urandom(10)
        random_int = int.from_bytes(random_bytes, byteorder='big')
        
        # Encode timestamp (10 caracteres)
        timestamp_str = ""
        ts = timestamp_ms
        for _ in range(10):
            timestamp_str = ENCODING[ts % 32] + timestamp_str
            ts //= 32
        
        # Encode random (16 caracteres)
        random_str = ""
        rand = random_int
        for _ in range(16):
            random_str = ENCODING[rand % 32] + random_str
            rand //= 32
        
        return timestamp_str + random_str
    
    def generate_batch_id(self, tick_number: int) -> str:
        """
        Genera Batch ID determinístico para un tick específico.
        
        Format: BATCH_{sequence}_{date}_{time_us}
        Example: BATCH_00000042_20251107_143052_123456
        
        Args:
            tick_number: Número de tick/batch secuencial
            
        Returns:
            Batch ID string
        """
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")
        microsec = now.microsecond
        
        return f"BATCH_{tick_number:08d}_{date_str}_{time_str}_{microsec:06d}"
    
    def generate_event_id(self, event_type: str, prev_hash: Optional[str] = None) -> str:
        """
        Genera Event ID con opcional chain linking.
        
        Format: EVT_{type}_{uuidv7}[_{prev_hash_prefix}]
        
        Args:
            event_type: Tipo de evento (SIGNAL, DECISION, EXECUTION, etc)
            prev_hash: Hash del evento anterior para linking
            
        Returns:
            Event ID string
        """
        uuid = self.generate_uuidv7()
        
        if prev_hash:
            # Include first 8 chars of previous hash for chain linking
            prefix = prev_hash[:8]
            return f"EVT_{event_type}_{uuid}_{prefix}"
        
        return f"EVT_{event_type}_{uuid}"
    
    def generate_data_slice_id(self, content_hash: str) -> str:
        """
        Genera Data Slice ID determinístico basado en contenido.
        
        Format: SLICE_{timestamp}_{content_hash_prefix}
        
        Args:
            content_hash: SHA256 hash del contenido del slice
            
        Returns:
            Data Slice ID string
        """
        timestamp = int(time.time() * 1000)
        hash_prefix = content_hash[:16]
        
        return f"SLICE_{timestamp}_{hash_prefix}"
    
    @staticmethod
    def extract_timestamp(id_string: str) -> Optional[int]:
        """
        Extrae timestamp de un ID monotónico.
        
        Args:
            id_string: ID string (UUIDv7, ULID, Batch ID, etc)
            
        Returns:
            Timestamp en milisegundos o None si no es extraible
        """
        # UUIDv7
        if len(id_string) == 36 and id_string.count('-') == 4:
            try:
                parts = id_string.split('-')
                time_high = int(parts[0], 16)
                time_mid = int(parts[1][:3], 16)
                timestamp_ms = (time_high << 16) | (time_mid << 4)
                return timestamp_ms
            except (ValueError, IndexError):
                pass
        
        # ULID
        if len(id_string) == 26:
            try:
                ENCODING = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
                timestamp_str = id_string[:10]
                timestamp_ms = 0
                for char in timestamp_str:
                    timestamp_ms = timestamp_ms * 32 + ENCODING.index(char)
                return timestamp_ms
            except (ValueError, IndexError):
                pass
        
        # Batch ID
        if id_string.startswith("BATCH_"):
            try:
                parts = id_string.split('_')
                date_str = parts[2]  # YYYYMMDD
                time_str = parts[3]  # HHMMSS
                dt = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
                return int(dt.timestamp() * 1000)
            except (ValueError, IndexError):
                pass
        
        return None


# Singleton global
_id_generator = IDGenerator()


def generate_batch_id(tick_number: int) -> str:
    """Genera Batch ID para un tick."""
    return _id_generator.generate_batch_id(tick_number)


def generate_event_id(event_type: str, prev_hash: Optional[str] = None) -> str:
    """Genera Event ID con opcional chain linking."""
    return _id_generator.generate_event_id(event_type, prev_hash)


def generate_uuidv7() -> str:
    """Genera UUIDv7."""
    return _id_generator.generate_uuidv7()


def generate_ulid() -> str:
    """Genera ULID."""
    return _id_generator.generate_ulid()


def generate_data_slice_id(content_hash: str) -> str:
    """Genera Data Slice ID."""
    return _id_generator.generate_data_slice_id(content_hash)


class DeterministicRandom:
    """
    Generador pseudoaleatorio determinístico con seed por tick.
    
    Permite reproducir exactamente las mismas "decisiones aleatorias"
    dado el mismo seed, crítico para replay y debugging.
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Inicializa generador determinístico.
        
        Args:
            seed: Seed inicial (default: timestamp actual)
        """
        self.seed = seed or int(time.time() * 1000000)
        self.rng = random.Random(self.seed)
    
    def set_seed_for_tick(self, tick_number: int, date_str: str):
        """
        Establece seed determinístico para un tick específico.
        
        El seed se calcula combinando tick_number y date para garantizar
        que el mismo tick en diferentes días tiene seeds diferentes,
        pero el mismo tick en replay tiene el mismo seed.
        
        Args:
            tick_number: Número de tick secuencial
            date_str: Fecha en formato YYYYMMDD
        """
        # Combinar tick y fecha para seed único pero determinístico
        combined = f"{date_str}_{tick_number:08d}"
        seed_value = hash(combined) & 0xFFFFFFFF  # 32-bit seed
        self.rng.seed(seed_value)
        self.seed = seed_value
    
    def random(self) -> float:
        """Genera float aleatorio entre 0.0 y 1.0."""
        return self.rng.random()
    
    def randint(self, a: int, b: int) -> int:
        """Genera int aleatorio entre a y b (inclusive)."""
        return self.rng.randint(a, b)
    
    def choice(self, seq):
        """Selecciona elemento aleatorio de una secuencia."""
        return self.rng.choice(seq)
    
    def uniform(self, a: float, b: float) -> float:
        """Genera float aleatorio uniforme entre a y b."""
        return self.rng.uniform(a, b)
    
    def gauss(self, mu: float, sigma: float) -> float:
        """Genera float aleatorio gaussiano con media mu y desviación sigma."""
        return self.rng.gauss(mu, sigma)
    
    def get_current_seed(self) -> int:
        """Retorna el seed actual."""
        return self.seed


# Singleton global determinístico
_deterministic_rng = DeterministicRandom()


def set_seed_for_tick(tick_number: int, date_str: str):
    """Establece seed determinístico para un tick."""
    _deterministic_rng.set_seed_for_tick(tick_number, date_str)


def get_deterministic_random() -> DeterministicRandom:
    """Obtiene el RNG determinístico global."""
    return _deterministic_rng
