from flask import render_template, request

def get_categorias(cursor):
    # Obtener las categorías disponibles para mostrar en el formulario
    cursor.execute("SELECT * FROM categorias WHERE activo = TRUE")
    return cursor.fetchall()

def register_routes(app, db, cursor):
    @app.route('/agregar-productos-form', methods=['GET', 'POST'])
    def agregar_productos():
        if request.method == 'POST':
            nombre_producto = request.form['nombre']
            marca = request.form['marca']
            precio = float(request.form['precio'])
            stock = float(request.form['stock'])
            categoria_id = int(request.form['categoria'])
            caducidad = request.form['caducidad']

            if stock <= 0:
                script = """
                    <script>
                        Swal.fire({
                            title: 'Error',
                            text: 'El stock debe ser mayor que 0.',
                            icon: 'error',
                            showCancelButton: false,
                            confirmButtonColor: '#3085d6',
                            confirmButtonText: 'Aceptar'
                        });
                    </script>
                """
                return render_template('agregar_productos.html', script=script, categorias=get_categorias(cursor))

            # Verificar si el producto ya existe en la base de datos
            cursor.execute("SELECT id FROM productos WHERE nombre = %s AND marca = %s AND categoria = %s",
                           (nombre_producto, marca, categoria_id))
            producto_existente = cursor.fetchone()

            if producto_existente:
                script = """
                    <script>
                        Swal.fire({
                            title: 'Error',
                            text: 'El producto ya existe.',
                            icon: 'error',
                            showCancelButton: false,
                            confirmButtonColor: '#3085d6',
                            confirmButtonText: 'Aceptar'
                        });
                    </script>
                """
                return render_template('agregar_productos.html', script=script, categorias=get_categorias(cursor))

            # Insertar el nuevo producto en la base de datos
            cursor.execute("INSERT INTO productos (nombre, marca, precio, stock, categoria, caducidad) VALUES (%s, %s, %s, %s, %s, %s)",
                           (nombre_producto, marca, precio, stock, categoria_id, caducidad))
            db.commit()

            # Mostrar ventana modal de éxito
            script = """
                <script>
                    Swal.fire({
                        title: 'Éxito',
                        text: 'Producto agregado correctamente.',
                        icon: 'success',
                        showCancelButton: false,
                        confirmButtonColor: '#3085d6',
                        confirmButtonText: 'Aceptar'
                    });
                </script>
            """
            return render_template('agregar_productos.html', script=script, categorias=get_categorias(cursor))

        # Obtener las categorías para mostrar en el formulario
        categorias = get_categorias(cursor)
        

        return render_template('agregar_productos.html', categorias=categorias)
