from flask import render_template, request, flash, redirect, jsonify
import json

def get_productos(cursor):
    cursor.execute("SELECT id, nombre, precio, stock FROM productos WHERE activo = TRUE")
    return cursor.fetchall()

def register_routes(app, db, cursor):
    @app.route('/agregar-venta', methods=['GET', 'POST'])
    def agregar_venta():
        if request.method == 'POST':
            producto_id = int(request.form['producto'])
            cantidad = float(request.form['cantidad'])
            unidad_medida = request.form['unidad_medida']

            cursor.execute("SELECT nombre, precio, stock FROM productos WHERE id = %s", (producto_id,))
            producto = cursor.fetchone()
            precio_unitario = producto[0]
            stock_actual = producto[1]

            if unidad_medida == 'gramo':
                cantidad = cantidad / 1000

            precio_unitario = float(precio_unitario)
            precio_total = precio_unitario * cantidad

            if cantidad > stock_actual:
                flash("No hay suficiente stock disponible para el producto seleccionado.", 'error')
                return redirect('/agregar-venta')

            if cantidad == 0:
                flash("Seleccione un valor válido.", 'error')
                return redirect('/agregar-venta')

            nuevo_stock = stock_actual - cantidad

            cursor.execute("INSERT INTO ventas (fecha, total) VALUES (NOW(), 0)")
            venta_id = cursor.lastrowid

            cursor.execute("INSERT INTO ventas_productos (venta_id, producto_id, cantidad, precio_total) VALUES (%s, %s, %s, %s)",
                        (venta_id, producto_id, cantidad, precio_total))
            db.commit()

            cursor.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (cantidad, producto_id))
            db.commit()

            flash("Producto agregado a la venta.", 'success')
            return redirect('/agregar-venta')

        productos = get_productos(cursor)
        return render_template('agregar_venta.html', productos=productos)

    @app.route('/guardar-venta', methods=['POST'])
    def guardar_venta():
        try:
            productos_agregados = json.loads(request.data)
            total_venta = sum(producto['cantidad'] * producto['precio_unitario'] for producto in productos_agregados)

            cursor.execute("INSERT INTO ventas (fecha, total) VALUES (NOW(), %s)", (total_venta,))
            venta_id = cursor.lastrowid

            for producto in productos_agregados:
                producto_id = producto['producto_id']
                cantidad = producto['cantidad']
                precio_unitario = producto['precio_unitario']

                cursor.execute("INSERT INTO ventas_productos (venta_id, producto_id, cantidad, precio_total) VALUES (%s, %s, %s, %s)",
                            (venta_id, producto_id, cantidad, cantidad * precio_unitario))
                
                cursor.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (cantidad, producto_id))
                db.commit()

            return jsonify({"success": True})
        except Exception as e:
            print("Error al guardar la venta:", str(e))
            return jsonify({"success": False})
