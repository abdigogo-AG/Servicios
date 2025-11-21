// Este script se ejecuta usando las credenciales ROOT que le dimos
// (admin_mongo / un_password_seguro_para_mongo)

// Usaremos una base de datos específica para nuestros datos de app
db = db.getSiblingDB('miAppDB');

// Crear la colección para reseñas
db.createCollection('resenas');

// Crear índices para búsquedas comunes
// (Ej: buscar reseñas por el ID de usuario o por el ID de un producto)
db.resenas.createIndex({ "id_usuario": 1 });
db.resenas.createIndex({ "id_producto": 1 });

// Crear la colección para fotos
db.createCollection('fotos');

// Crear un índice para buscar fotos por el usuario que las subió
db.fotos.createIndex({ "id_usuario": 1 });

print("✅ Colecciones 'resenas' y 'fotos' e índices creados en 'miAppDB'.");