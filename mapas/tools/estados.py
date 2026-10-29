"""INEGI state codes (entidades federativas) and a tolerant name resolver."""
import unicodedata

ESTADOS = {
    "01": "Aguascalientes", "02": "Baja California", "03": "Baja California Sur",
    "04": "Campeche", "05": "Coahuila de Zaragoza", "06": "Colima", "07": "Chiapas",
    "08": "Chihuahua", "09": "Ciudad de México", "10": "Durango", "11": "Guanajuato",
    "12": "Guerrero", "13": "Hidalgo", "14": "Jalisco", "15": "México",
    "16": "Michoacán de Ocampo", "17": "Morelos", "18": "Nayarit", "19": "Nuevo León",
    "20": "Oaxaca", "21": "Puebla", "22": "Querétaro", "23": "Quintana Roo",
    "24": "San Luis Potosí", "25": "Sinaloa", "26": "Sonora", "27": "Tabasco",
    "28": "Tamaulipas", "29": "Tlaxcala", "30": "Veracruz de Ignacio de la Llave",
    "31": "Yucatán", "32": "Zacatecas",
}

# Capital city of each state, (lat, lng) rounded to about 1 km. Used to center the map when a state
# is picked; approximate on purpose, not an official centroid.
CAPITALES = {
    "01": (21.8853, -102.2916), "02": (32.6245, -115.4523), "03": (24.1426, -110.3128),
    "04": (19.8301, -90.5349), "05": (25.4232, -101.0053), "06": (19.2433, -103.7250),
    "07": (16.7528, -93.1152), "08": (28.6353, -106.0889), "09": (19.4326, -99.1332),
    "10": (24.0277, -104.6532), "11": (21.0190, -101.2574), "12": (17.5506, -99.5058),
    "13": (20.1011, -98.7591), "14": (20.6597, -103.3496), "15": (19.2826, -99.6557),
    "16": (19.7060, -101.1950), "17": (18.9186, -99.2342), "18": (21.5058, -104.8946),
    "19": (25.6866, -100.3161), "20": (17.0732, -96.7266), "21": (19.0414, -98.2063),
    "22": (20.5888, -100.3899), "23": (18.5001, -88.2961), "24": (22.1565, -100.9855),
    "25": (24.8091, -107.3940), "26": (29.0729, -110.9559), "27": (17.9892, -92.9475),
    "28": (23.7369, -99.1411), "29": (19.3139, -98.2404), "30": (19.5438, -96.9102),
    "31": (20.9674, -89.5926), "32": (22.7709, -102.5832),
}

# "México" alone is the Estado de México (15), so the usual shortcuts are explicit.
_ALIAS = {"cdmx": "09", "df": "09", "edomex": "15", "estado de mexico": "15", "mexico": "15"}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.strip().lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def resolver_estado(valor: str) -> str:
    """Return the two-digit INEGI code for a code, name, shortcut or unambiguous prefix."""
    v = _norm(str(valor))
    if v.isdigit() and v.zfill(2) in ESTADOS:
        return v.zfill(2)
    if v in _ALIAS:
        return _ALIAS[v]
    nombres = {_norm(n): c for c, n in ESTADOS.items()}
    if v in nombres:
        return nombres[v]
    candidatos = {c for n, c in nombres.items() if n.startswith(v)} if v else set()
    if len(candidatos) == 1:
        return candidatos.pop()
    raise ValueError(f"estado no reconocido o ambiguo: {valor!r}")
