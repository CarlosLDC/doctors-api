import requests
from bs4 import BeautifulSoup
import re
import json

# Encabezados para la solicitud
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, como Gecko) Chrome/58.0.3029.110 Safari/537.3 Edge/16.16299'
}

def obtener_contenido(url):
    """Realiza una solicitud GET y obtiene el contenido HTML."""
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return BeautifulSoup(response.content, 'html.parser')
    else:
        print(f"Error al realizar la solicitud: {response.status_code}")
        return None

def extraer_nombre_doctor(doctor_soup):
    """Extrae el nombre del doctor a partir de la etiqueta <title>."""
    title_tag = doctor_soup.find('title')
    if title_tag:
        title_text = title_tag.text
        nombre_doctor = title_text.split('-')[0].strip()
        return nombre_doctor
    return "unknown_name"

def extraer_thumbnail_url(doctor_soup):
    """Extrae la URL de la imagen de perfil del doctor a partir del texto 'thumbnailUrl'."""
    script_tags = doctor_soup.find_all('script', type='application/ld+json')
    for tag in script_tags:
        tag_content = tag.string
        if tag_content and 'thumbnailUrl' in tag_content:
            match = re.search(r'"thumbnailUrl":\s*"([^"]+)"', tag_content)
            if match:
                return match.group(1)
    return "unknown_thumbnail"

def formatear_nombre(nombre):
    """Formatea el nombre para que solo la primera letra de cada palabra esté en mayúsculas."""
    return nombre.title()

def clasificar_texto(texto):
    """Clasifica el texto en las categorías especificadas."""
    clasificacion = {
        "hospital": '',
        "office": '',
        "location": '',
        "schedule": '',
        "phones": []
    }
    partes = texto.split('_')
    for parte in partes:
        parte = parte.strip()
        if 'clínica' in parte.lower():
            clasificacion["hospital"] = formatear_nombre(parte)
        elif 'consultorio' in parte.lower():
            clasificacion["office"] = parte
        elif 'estado' in parte.lower():
            clasificacion["location"] = parte
        elif any(dia in parte.lower() for dia in ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']):
            clasificacion["schedule"] = parte
        elif 'teléfono' in parte.lower():
            telefonos = re.sub(r'[^0-9/]', '', parte).split('/')
            clasificacion["phones"].extend(telefonos)
    return clasificacion

def procesar_doctor_url(doctor_url, especialidad):
    """Procesa la URL de cada doctor, extrayendo y clasificando la información."""
    if not doctor_url.startswith('http'):
        doctor_url = 'https://guiasaludyvida.com' + doctor_url
    
    doctor_soup = obtener_contenido(doctor_url)
    if doctor_soup:
        nombre_doctor = extraer_nombre_doctor(doctor_soup)
        thumbnail_url = extraer_thumbnail_url(doctor_soup)
        first_paragraph = doctor_soup.find('p')
        if first_paragraph and 'td-post-sub-title' not in first_paragraph.get('class', []):
            paragraph_html = str(first_paragraph)
            paragraph_cleaned = re.sub(r'<[^>]+>', '_', paragraph_html)
            paragraph_cleaned = re.sub(r':', '', paragraph_cleaned)
            paragraph_cleaned = re.sub(r'\s+', ' ', paragraph_cleaned).strip()
            paragraph_cleaned = re.sub(r'_+', '_', paragraph_cleaned).strip('_')
            clasificacion = clasificar_texto(paragraph_cleaned)
            return {
                "name": nombre_doctor,
                "specialties": [especialidad],
                "url": doctor_url,
                "thumbnail": thumbnail_url,
                **clasificacion
            }
    return None

def combinar_especialidades(data, doctor_data):
    """Combina las especialidades si el doctor ya existe en la lista."""
    for item in data:
        if item['name'] == doctor_data['name']:
            item['specialties'] = list(set(item['specialties'] + doctor_data['specialties']))
            return
    data.append(doctor_data)

def main(base_urls):
    data = []
    
    for base_url in base_urls:
        especialidad = determinar_especialidad(base_url)
        soup = obtener_contenido(base_url)
        if soup:
            doctor_links = soup.find_all('a', title=lambda t: t and ('Dr.' in t or 'Dra.' in t))
            urls = {link.get('href') for link in doctor_links}
            
            for doctor_url in urls:
                doctor_data = procesar_doctor_url(doctor_url, especialidad)
                if doctor_data:
                    combinar_especialidades(data, doctor_data)

    # Convertir la lista a formato JSON y guardarla en un archivo
    data_json = json.dumps(data, indent=4, ensure_ascii=False)
    with open('doctors.json', 'w', encoding='utf-8') as f:
        f.write(data_json)
        print("Archivo 'doctors.json' guardado con éxito.")

def determinar_especialidad(base_url):
    """Determina la especialidad basada en el URL base."""
    if "cirugia-oncologica" in base_url:
        return "oncología"
    elif "cirugia-mastologia" in base_url:
        return "mastología"
    else:
        return "desconocida"

if __name__ == '__main__':
    # URLs a evaluar
    base_urls = [
        'https://guiasaludyvida.com/cirugia-oncologica/',
        'https://guiasaludyvida.com/directorio-medico/especialidades-medicas/cirugia-mastologia/'
    ]
    main(base_urls)


