
// 1. AL CARGAR LA PÁGINA: REVISAR SESIÓN
document.addEventListener('DOMContentLoaded', () => {
    const usuarioId = localStorage.getItem("usuario_id");
    const usuarioNombre = localStorage.getItem("usuario_nombre");
    // const esTrabajador = localStorage.getItem("es_trabajador"); // Si tuviéramos este dato guardado

    const navGuest = document.getElementById('nav-guest');
    const navLogged = document.getElementById('nav-logged');
    const btnTrabajador = document.getElementById('btn-hero-trabajador');

    if (usuarioId) {
        // === MODO SESIÓN INICIADA ===
        navGuest.classList.add('d-none'); // Ocultar Login/Registro
        navLogged.classList.remove('d-none'); // Mostrar Hola + Salir
        document.getElementById('user-name').innerText = "Hola, " + usuarioNombre;

        // Si ya está logueado como cliente, ocultamos "Quiero Trabajar"
        // (Asumiendo que por defecto es cliente, o podrías guardar el rol en localStorage al hacer login)
        if (btnTrabajador) {
            btnTrabajador.style.display = 'none';
        }
    } else {
        // === MODO INVITADO ===
        navGuest.classList.remove('d-none');
        navLogged.classList.add('d-none');
    }
});

// 2. FUNCIÓN CERRAR SESIÓN
function cerrarSesion() {
    if (confirm("¿Seguro que quieres cerrar sesión?")) {
        localStorage.clear(); // Borra los datos de sesión
        window.location.reload(); // Recarga la página para volver al modo invitado
    }
}

// 3. GUARDAR PREFERENCIA (Para invitados)
function guardarPreferencia(rol) {
    localStorage.setItem('rol_preferido', rol);
}

// 4. VERIFICAR ANTES DE PEDIR SERVICIO
function verificarSesionAntes(e, rol) {
    const usuarioId = localStorage.getItem("usuario_id");

    if (!usuarioId) {
        // Si no está logueado, lo mandamos al registro pero guardamos que quiere ser cliente
        e.preventDefault();
        guardarPreferencia('cliente');
        window.location.href = "principal.html?rol=cliente";
    }
    // Si está logueado, el enlace href="publicar.html" funciona normal
}