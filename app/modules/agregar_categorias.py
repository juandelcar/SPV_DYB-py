from flask import render_template, request

def register_routes(app, db, cursor):
    @app.route('/agregar-categorias-form', methods=['GET', 'POST'])
    def agregar_categorias():
        if request.method == 'POST':
            nombre_categoria = request.form['nombre']

            # Insertar la nueva categoría en la base de datos
            cursor.execute("INSERT INTO categorias (nombre) VALUES (%s)", (nombre_categoria,))
            db.commit()

            # Mostrar mensaje emergente de éxito
            script = """
                <script>
                    Swal.fire({
                        title: '¡Éxito!',
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
