/*
██╗   ██╗ █████╗ ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗ ██████╗ ██████╗ 
██║   ██║██╔══██╗████╗  ██║██╔════╝ ██║   ██║██╔══██╗██╔══██╗██╔══██╗
██║   ██║███████║██╔██╗ ██║██║  ███╗██║   ██║███████║██████╔╝██║  ██║
╚██╗ ██╔╝██╔══██║██║╚██╗██║██║   ██║██║   ██║██╔══██║██╔══██╗██║  ██║
 ╚████╔╝ ██║  ██║██║ ╚████║╚██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝
  ╚═══╝  ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ 

                              ██╗ █████╗ 
                              ██║██╔══██╗
                              ██║███████║
                              ██║██╔══██║
                              ██║██║  ██║
                              ╚═╝╚═╝  ╚═╝
*/

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(loginForm);
            const data = Object.fromEntries(formData.entries());

            const button = loginForm.querySelector('button[type="submit"]');
            const buttonText = button.querySelector('.button-text');
            const spinner = button.querySelector('.spinner');
            const errorMessageDiv = document.getElementById('errorMessage');

            button.disabled = true;
            buttonText.style.display = 'none';
            spinner.style.display = 'block';
            errorMessageDiv.style.display = 'none';

            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (response.ok) {

                    window.location.href = '/inicio'; 
                } else {
                    errorMessageDiv.textContent = result.error || 'Error desconocido.';
                    errorMessageDiv.style.display = 'block';
                }
            } catch (error) {
                errorMessageDiv.textContent = 'Error de conexión con el servidor.';
                errorMessageDiv.style.display = 'block';
            } finally {

                button.disabled = false;
                buttonText.style.display = 'inline';
                spinner.style.display = 'none';
            }
        });
    }

    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const password = registerForm.querySelector('#password').value;
            const confirmPassword = registerForm.querySelector('#confirmPassword').value;
            const errorMessageDiv = document.getElementById('errorMessage');
            const successMessageDiv = document.getElementById('successMessage');

            errorMessageDiv.style.display = 'none';
            successMessageDiv.style.display = 'none';

            if (password !== confirmPassword) {
                errorMessageDiv.textContent = 'Las contraseñas no coinciden.';
                errorMessageDiv.style.display = 'block';
                return;
            }
            if (password.length < 8) {
                errorMessageDiv.textContent = 'La contraseña debe tener al menos 8 caracteres.';
                errorMessageDiv.style.display = 'block';
                return;
            }

            const formData = new FormData(registerForm);
            const data = Object.fromEntries(formData.entries());
            delete data.confirmPassword;

            const button = registerForm.querySelector('button[type="submit"]');
            const buttonText = button.querySelector('.button-text');
            const spinner = button.querySelector('.spinner');

            button.disabled = true;
            buttonText.style.display = 'none';
            spinner.style.display = 'block';

            try {
                const response = await fetch('/api/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (response.ok) {
                    successMessageDiv.textContent = '¡Registro exitoso! Serás redirigido para iniciar sesión.';
                    successMessageDiv.style.display = 'block';
                    registerForm.reset(); 

                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 2000);
                } else {
                    errorMessageDiv.textContent = result.error || 'Ocurrió un error durante el registro.';
                    errorMessageDiv.style.display = 'block';
                }
            } catch (error) {
                errorMessageDiv.textContent = 'Error de conexión con el servidor.';
                errorMessageDiv.style.display = 'block';
            } finally {
                button.disabled = false;
                buttonText.style.display = 'inline';
                spinner.style.display = 'none';
            }
        });
    }
});