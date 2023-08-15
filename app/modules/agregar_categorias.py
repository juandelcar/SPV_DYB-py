from flask import render_template, request

def register_routes(app, db, cursor):
    @app.route('/agregar-categorias-form', methods=['GET', 'POST'])
    def agregar_categorias():
        if request.method == 'POST':
            nombre_categoria = request.form['nombre']

            # Verificar si la categoría ya existe en la base de datos
            cursor.execute("SELECT nombre FROM categorias WHERE nombre = %s", (nombre_categoria,))
            existing_category = cursor.fetchone()

            if existing_category:
                script = """
                    <script>
                        Swal.fire({
                            title: 'Error',
                            text: 'La categoría ya existe. Por favor, elija otro nombre.',
                            icon: 'error',
                            showCancelButton: false,
                            confirmButtonColor: '#3085d6',
                            confirmButtonText: 'Aceptar'
                        }).then((result) => {
                            if (result.isConfirmed) {
                                window.location.href = '/agregar-categorias-form';
                            }
                        });
                    </script>
                """
                return render_template('agregar_categorias.html', script=script)

            # Insertar la nueva categoría en la base de datos
            cursor.execute("INSERT INTO categorias (nombre) VALUES (%s)", (nombre_categoria,))
            db.commit()

            # Mostrar mensaje emergente de éxito
            script = """
                <script>
                    Swal.fire({
                        title: 'Éxito',
                        text: 'Categoría agregada correctamente.',
                        icon: 'success',
                        showCancelButton: false,
                        confirmButtonColor: '#3085d6',
                        confirmButtonText: 'Aceptar'
                    });
                </script>
            """
            return render_template('agregar_categorias.html', script=script)

        return render_template('agregar_categorias.html')
