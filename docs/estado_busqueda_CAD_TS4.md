# Búsqueda CAD ABB para TS4

Fecha de revisión: 15 de noviembre de 2026.

## CAD descargados

El archivo `ABB_CAD_TS4_Argentina.zip` contiene 12 archivos de ABB Library, con tamaño, identificador de documento y SHA-256 en `datos/cad_argentina.json`. Se comprobó la integridad de los 12 archivos dentro del ZIP. Incluye XT1, XT2, S800 4P, S201M 1P, S201M Na 1P+N y OT315/OT400E04. El S201M 1P es una referencia complementaria y no representa QF90.

## Correcciones del unifilar

- **QF90:** S201M-C10NA, 1P+N, 10 A, 10 kA, código ABB `2CDS271103R0104`. Se añadieron DWG 2D `9AKK106930A4857` y STEP 3D `9AKK106930A4835` de la carcasa 1P+N. El dibujo de frente del editor todavía es una interpretación vectorial, no la geometría CAD ABB insertada.
- **QF89:** S251 Na C10, 1P+N, 6 kA, código histórico ABB `16060722 / EF0722`. No se localizó CAD oficial ni evidencia de oferta argentina actual. Su geometría en el editor continúa provisional.
- **Envolvente:** el catálogo ABB 185 mm confirma las dimensiones funcionales 1000 × 2100 × 500 mm y la pieza lateral `PFCM0500`; se corrigió la referencia escrita antes como `PCFM0500`. No se verificó oferta argentina de la configuración completa ni se consiguió un CAD oficial descargable del gabinete exacto y sus kits. La posición elegida para el riel DIN sigue pendiente de validar con el armado ABB.
- **XT2N TMG 80-240 4P:** código ABB `1SDA067734R1` confirmado en catálogo. Hay CAD oficial de carcasa 4P, pero no se verificó una publicación argentina de esa variante exacta.

## Fuentes principales

- Catálogo ABB System pro E power 185 mm: https://library.e.abb.com/public/ea19569e71bd4a55ac10d34ebc2c89d8/Katalog_185_1STC803009D0103%20SPEP%20185%20catalogue%202024%20Rev%203.pdf
- Catálogo histórico ABB S251: https://library.e.abb.com/public/904c32994f43cc7fc1256cb00053600f/ITSCE-603221011.pdf
- Catálogo ABB S201M-C10NA: https://library.e.abb.com/public/ac7ba9f0b2fe4959848cfa4f6e8a7e2e/A_ELSB_Catalogue_2024_1st_Edition%202%20_MCB.pdf
- Certificado ABB Argentina S200M: https://new.abb.com/docs/librariesprovider78/argentina/electrification/%28pos-10%29--31-01-2025---s200m---dc-e-t26-022-4-%28m3%29.pdf?sfvrsn=e88fd30c_1
- ABB Library CAD 2D S201M Na: https://search.abb.com/library/Download.aspx?Action=Launch&DocumentID=9AKK106930A4857&DocumentPartId=&DocumentRevisionId=-&LanguageCode=en
- ABB Library CAD 3D S200M 1P+N: https://search.abb.com/library/Download.aspx?Action=Launch&DocumentID=9AKK106930A4835&DocumentPartId=&DocumentRevisionId=-&LanguageCode=en
- Catálogo ABB XT2 códigos: https://library.e.abb.com/public/ddc75d0d00fd49debf248aa8d8d6e43c/1SDC210100D0904_D.pdf

## Pendientes para fabricación

Confirmar por canal ABB Argentina disponibilidad del gabinete exacto, riel y kits, XT2 exacto y sustitución o provisión del S251 histórico. Integrar los CAD reales en la vista y exportación AutoCAD; el editor actual no lo hace todavía. Verificar disposición de rieles y barras con la configuración de gabinete aprobada.
