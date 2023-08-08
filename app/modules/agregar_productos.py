from flask import render_template, request, flash

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

            # Verificar si el producto ya existe en la base de datos
            cursor.execute("SELECT id FROM productos WHERE nombre = %s AND marca = %s AND precio = %s AND stock = %s AND categoria = %s AND caducidad = %s",
                           (nombre_producto, marca, precio, stock, categoria_id, caducidad))
            producto_existente = cursor.fetchone()

            if producto_existente:
                flash("¡El producto ya existe!", 'warning')
            else:
                # Insertar el nuevo producto en la base de datos
                cursor.execute("INSERT INTO productos (nombre, marca, precio, stock, categoria, caducidad) VALUES (%s, %s, %s, %s, %s, %s)",
                               (nombre_producto, marca, precio, stock, categoria_id, caducidad))
                db.commit()

                # Mostrar mensaje emergente de éxito usando flash message
                flash("¡Producto agregado correctamente!", 'success')

        # Obtener las categorías para mostrar en el formulario
        categorias = get_categorias(cursor)

        return render_template('agregar_productos.html', categorias=categorias)
