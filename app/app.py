from flask import Flask, render_template, request, redirect, session, flash, Response, send_from_directory
import mysql.connector
from modules import agregar_productos, agregar_categorias, agregar_venta
from math import ceil
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from io import BytesIO
from reportlab.lib.styles import getSampleStyleSheet
import bcrypt
import pandas as pd






app = Flask(__name__)

# Configuración de la base de datos
db = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    database='spv_dybj'
)
cursor = db.cursor()


# Configuración de la clave secreta para sesiones
app.secret_key = 'tu_clave_secreta'

@app.route('/encrypt-passwords', methods=['GET'])
def encrypt_passwords():
    # Obtener todos los usuarios desde la base de datos
    cursor.execute("SELECT id, contrasena FROM usuario")
    usuarios = cursor.fetchall()

    for usuario in usuarios:
        user_id = usuario[0]
        original_password_hash = usuario[1]

        # Verificar si la contraseña ya está encriptada (si contiene el prefijo '$2b$')
        if not original_password_hash.startswith('$2b$'):
            # Encriptar la contraseña original utilizando bcrypt
            encrypted_password_hash = bcrypt.hashpw(original_password_hash.encode('utf-8'), bcrypt.gensalt())

            # Actualizar la contraseña encriptada en la base de datos
            cursor.execute("UPDATE usuario SET contrasena = %s WHERE id = %s", (encrypted_password_hash, user_id))
            db.commit()

    return "Contraseñas encriptadas correctamente."

# Ruta para el inicio de sesión
@app.route('/', methods=['GET', 'POST'])
def login():
    error_message = ''  # Inicializar el mensaje de error

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Verificar las credenciales del usuario en la base de datos
        cursor.execute("SELECT id, nombre_usuario, contrasena FROM usuario WHERE nombre_usuario = %s", (username,))
        user = cursor.fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            # Iniciar sesión almacenando el ID y nombre del usuario en la sesión
            session['user_id'] = user[0]
            session['nombre_usuario'] = user[1]
            return redirect('/principal')
        else:
            error_message = 'Usuario y/o contraseña incorrectos. Verifica e inténtelo de nuevo.'

    return render_template('login.html', error_message=error_message)





@app.route('/terminos-condiciones')
def terminos_condiciones():
    return render_template('terminos-condiciones.html')



# Ruta para la página principal
@app.route('/principal')
def principal():
    # Verificar si el usuario está logueado (existe en la sesión)
    if 'user_id' in session:
        # Obtener el ID del usuario desde la sesión
        user_id = session.get('user_id')

        # Consultar el nombre del usuario en la base de datos
        cursor.execute("SELECT nombre_usuario FROM usuario WHERE id = %s", (user_id,))
        user = cursor.fetchone()

        if user:
            nombre_usuario = user[0]
        else:
            nombre_usuario = "Usuario Desconocido"  # En caso de que no se encuentre el usuario en la base de datos

        # Lista de acciones para el menú (puedes agregar más)
        menu_acciones = ['Agregar Productos', 'Agregar Categorías', 'Agregar Venta', 'Editar Productos', 'Editar Categorías', 'Buscar Productos', 'Subir Productos(Excel)','Productos Existentes..(PDF)', 'Categorias Existentes..(PDF)', 'Historial de Ventas..(PDF)', 'Productos Caducados..(PDF)']

        # Obtener la fecha y hora actual
        fecha_actual = datetime.now().strftime('%Y-%m-%d')

        return render_template('principal.html', acciones=menu_acciones, nombre_usuario=nombre_usuario, fecha_actual=fecha_actual)
    else:
        return redirect('/')


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)







# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    # Eliminar la información de la sesión para cerrarla
    session.clear()

    # Redirigir al inicio de sesión
    return redirect('/')
@app.after_request
def add_no_cache_headers(response):
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

# Registrar las rutas de los módulos
agregar_productos.register_routes(app, db, cursor)
agregar_categorias.register_routes(app, db, cursor)
agregar_venta.register_routes(app, db, cursor)





@app.route('/buscar-productos', methods=['GET', 'POST'])
def buscar_productos():
    if request.method == 'POST':
        filtro = request.form['filtro']
        valor_filtro = request.form['valor_filtro']

        # Modificar la consulta si el filtro es "categoria" para obtener el nombre de la categoría
        if filtro == 'categoria':
            cursor.execute("""
                SELECT p.id, p.nombre, p.marca, p.precio, p.stock, c.nombre AS categoria, p.caducidad 
                FROM productos p 
                JOIN categorias c ON p.categoria = c.id
                WHERE c.nombre LIKE %s 
                ORDER BY p.nombre ASC
            """, ('%' + valor_filtro + '%',))
        elif filtro == 'stock':
            try:
                # Si el filtro es por stock, convertimos el valor a un número entero
                valor_filtro = int(valor_filtro)
            except ValueError:
                # Si el valor no es un número válido, retornamos una lista vacía
                productos = []
            else:
                cursor.execute("""
                    SELECT p.id, p.nombre, p.marca, p.precio, p.stock, c.nombre AS categoria, p.caducidad 
                    FROM productos p 
                    JOIN categorias c ON p.categoria = c.id
                    WHERE p.stock = %s 
                    ORDER BY p.nombre ASC
                """, (valor_filtro,))
        else:
            # Para otros filtros, realizamos una búsqueda que coincide con el valor ingresado
            cursor.execute("""
                SELECT p.id, p.nombre, p.marca, p.precio, p.stock, c.nombre AS categoria, p.caducidad 
                FROM productos p 
                JOIN categorias c ON p.categoria = c.id
                WHERE {filtro} LIKE %s 
                ORDER BY p.nombre ASC
            """.format(filtro=filtro), ('%' + valor_filtro + '%',))
        
        productos = cursor.fetchall()
        return render_template('buscar_productos.html', productos=productos)

    # Obtener todos los productos y sus categorías cuando se carga la página inicialmente
    cursor.execute("""
        SELECT p.id, p.nombre, p.marca, p.precio, p.stock, c.nombre AS categoria, p.caducidad 
        FROM productos p 
        JOIN categorias c ON p.categoria = c.id WHERE p.activo = TRUE
        ORDER BY p.nombre ASC
    """)

    

    productos = cursor.fetchall()
    return render_template('buscar_productos.html', productos=productos)






# Ruta para la página de editar productos con paginador
@app.route('/editar-productos', methods=['GET'])
def editar_productos():
    # Obtener todos los productos desde la base de datos
    cursor.execute("SELECT p.id, p.nombre, p.marca, p.precio, p.stock, c.nombre AS categoria, p.caducidad FROM productos p JOIN categorias c ON p.categoria = c.id WHERE p.activo = TRUE ORDER BY p.nombre ASC")
    productos = cursor.fetchall()

    # Paginación
    productos_por_pagina = 10  # Cantidad de productos por página
    num_pagina = request.args.get('p', 1, type=int)
    total_productos = len(productos)
    num_paginas = ceil(total_productos / productos_por_pagina)

    # Limitar los productos por página
    inicio = (num_pagina - 1) * productos_por_pagina
    fin = inicio + productos_por_pagina
    productos_pagina = productos[inicio:fin]

    paginas = range(1, num_paginas + 1)

    return render_template('editar_productos.html', productos=productos_pagina, paginas=paginas, pagina_actual=num_pagina, num_paginas=num_paginas)


@app.route('/editar-producto/<int:producto_id>', methods=['GET', 'POST'])
def editar_producto(producto_id):
    if request.method == 'POST':
        # Obtener los datos actualizados del formulario
        nombre_producto = request.form['nombre']
        marca = request.form['marca']
        precio = float(request.form['precio'])
        stock = float(request.form['stock'])
        categoria = int(request.form['categoria'])
        caducidad = request.form['caducidad']

        # Actualizar el producto en la base de datos
        cursor.execute("UPDATE productos SET nombre = %s, marca = %s, precio = %s, stock = %s, categoria = %s, caducidad = %s WHERE id = %s",
                       (nombre_producto, marca, precio, stock, categoria, caducidad, producto_id))
        db.commit()

        flash("¡Producto actualizado correctamente!", 'success')
        return redirect('/editar-productos')

    # Obtener los datos del producto a editar desde la base de datos
    cursor.execute("SELECT * FROM productos WHERE id = %s", (producto_id,))
    producto = cursor.fetchone()

    if not producto:
        flash("Producto no encontrado", 'error')
        return redirect('/editar-productos')

    # Obtener todas las categorías desde la base de datos para mostrar en el formulario
    cursor.execute("SELECT * FROM categorias WHERE activo = TRUE")
    categorias = cursor.fetchall()

    return render_template('editar_producto.html', producto=producto, categorias=categorias)

@app.route('/eliminar-producto/<int:producto_id>', methods=['GET'])
def eliminar_producto(producto_id):
    # Eliminar el producto de la base de datos
    cursor.execute("UPDATE productos SET activo = FALSE WHERE id = %s", (producto_id,))
    db.commit()

    flash("¡Producto eliminado correctamente!", 'success')
    return redirect('/editar-productos')





@app.route('/editar-categorias', methods=['GET'])
def editar_categorias():
    # Obtener todas las categorías desde la base de datos
    cursor.execute("SELECT * FROM categorias WHERE activo = TRUE ORDER BY nombre ASC")
    categorias = cursor.fetchall()

    # Paginación
    categorias_por_pagina = 10  # Cantidad de categorías por página
    num_pagina = request.args.get('p', 1, type=int)
    total_categorias = len(categorias)
    num_paginas = ceil(total_categorias / categorias_por_pagina)

    # Limitar las categorías por página
    inicio = (num_pagina - 1) * categorias_por_pagina
    fin = inicio + categorias_por_pagina
    categorias_pagina = categorias[inicio:fin]

    paginas = range(1, num_paginas + 1)

    return render_template('editar_categorias.html', categorias=categorias_pagina, paginas=paginas, pagina_actual=num_pagina, num_paginas=num_paginas)

@app.route('/editar-categoria/<int:categoria_id>', methods=['GET', 'POST'])
def editar_categoria(categoria_id):
    if request.method == 'POST':
        # Obtener los datos actualizados del formulario
        nombre_categoria = request.form['nombre']

        # Actualizar la categoría en la base de datos
        cursor.execute("UPDATE categorias SET nombre = %s WHERE id = %s",
                       (nombre_categoria, categoria_id))
        db.commit()

        flash("¡Categoría actualizada correctamente!", 'success')
        return redirect('/editar-categorias')

    # Obtener los datos de la categoría a editar desde la base de datos
    cursor.execute("SELECT * FROM categorias WHERE id = %s", (categoria_id,))
    categoria = cursor.fetchone()

    if not categoria:
        flash("Categoría no encontrada", 'error')
        return redirect('/editar-categorias')

    return render_template('editar_categoria.html', categoria=categoria)

@app.route('/eliminar-categoria/<int:categoria_id>', methods=['GET'])
def eliminar_categoria(categoria_id):
    # Eliminar la categoría de la base de datos
    cursor.execute("UPDATE categorias SET activo = FALSE WHERE id = %s", (categoria_id,))
    db.commit()

    flash("¡Categoría eliminada correctamente!", 'success')
    return redirect('/editar-categorias')






# Ruta para generar el reporte de inventario actual en PDF
@app.route('/reporte-inventario')
def generar_reporte_inventario():
        # Realizar la consulta a la base de datos para obtener el inventario de productos
        cursor.execute("""
            SELECT p.nombre, p.marca, p.precio, p.stock, c.nombre AS categoria, p.caducidad 
            FROM productos p JOIN categorias c ON p.categoria = c.id WHERE p.activo = TRUE
            ORDER BY p.nombre ASC
        """)
        inventario = cursor.fetchall()

        # Crear el documento PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []


        # Agregar título al reporte
        styles = getSampleStyleSheet()
        titulo = Paragraph("Lista de productos en stock Judoyeli", styles['Title'])
        elements.append(titulo)

        elements.append(Spacer(1, 12))

        # Agregar encabezado al reporte
        encabezado = ("Nombre", "Marca", "Precio", "Stock (Kg/U)", "Categoría", "Caducidad")
        data = [encabezado] + [(producto[0], producto[1], producto[2], producto[3], producto[4], producto[5]) for producto in inventario]
        table = Table(data, colWidths=[125, 80, 60, 46, 125, 80], repeatRows=1)
        elements.append(table)

        # Estilo de la tabla
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1,colors.HexColor("#e0e0d1")),
            # Añadir margen a la tabla
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            # Reducir tamaño de fuente
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ])
        table.setStyle(style)

        # Construir el PDF
        doc.build(elements)

        # Crear la respuesta con el contenido del PDF
        response = Response(buffer.getvalue())

        # Establecer el encabezado Content-Disposition para cambiar el nombre del archivo al descargarlo
        nombre_archivo = "Lista de productos en stock Judoyeli.pdf"
        response.headers["Content-Disposition"] = f"inline; filename={nombre_archivo}"

        # Establecer el tipo de contenido como PDF
        response.headers["Content-Type"] = "application/pdf"

        return response


@app.route('/reporte-categorias')
def generar_reporte_categorias():
    # Realizar la consulta a la base de datos para obtener el inventario de productos
    cursor.execute("""
        SELECT * FROM categorias WHERE activo = TRUE
    """)
    inventario = cursor.fetchall()

    # Crear el documento PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # Agregar título al reporte
    styles = getSampleStyleSheet()
    titulo = Paragraph("Lista de Categorias existentes Judoyeli", styles['Title'])
    elements.append(titulo)

    elements.append(Spacer(1, 12))
    encabezado = ("ID", "Nombre")
    data = [encabezado] + [(categoria[0], categoria[1]) for categoria in inventario]
    table = Table(data, colWidths=[50, 250], repeatRows=1)
    elements.append(table)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#e0e0d1")),
        # Añadir margen a la tabla
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        # Reducir tamaño de fuente
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ])
    table.setStyle(style)

    # Construir el PDF
    doc.build(elements)
    response = Response(buffer.getvalue())

    # Establecer el encabezado Content-Disposition para cambiar el nombre del archivo al descargarlo
    nombre_archivo = "Lista de Categorias Existentes Judoyeli.pdf"
    response.headers["Content-Disposition"] = f"inline; filename={nombre_archivo}"

    # Establecer el tipo de contenido como PDF
    response.headers["Content-Type"] = "application/pdf"

    return response



# Ruta para generar el reporte de ventas en PDF
@app.route('/reporte-ventas')
def generar_reporte_ventas():
        # Realizar la consulta a la base de datos para obtener las ventas realizadas
        cursor.execute("""
            SELECT v.id AS venta_id, p.nombre AS producto, vp.cantidad AS cantidad, vp.precio_total AS total_producto, v.fecha, v.total
            FROM ventas v
            JOIN ventas_productos vp ON v.id = vp.venta_id
            JOIN productos p ON vp.producto_id = p.id 
            
        """)
        ventas = cursor.fetchall()

        # Crear el documento PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []

        # Agregar título al reporte
        titulo = "Lista de ventas generadas Judoyeli"
        style_heading = getSampleStyleSheet()["Heading1"]
        style_heading.alignment = 1  # Alinear el título al centro (0: izquierda, 1: centro, 2: derecha)
        elements.append(Paragraph(titulo, style_heading))

        # Espacio separador
        elements.append(Spacer(1, 15))

        # Encabezado de la tabla
        encabezado = ("ID Venta", "Producto(s)", "Total Venta", "Fecha")
        data = [encabezado]  # Iniciar con el encabezado

        # Agregar datos de ventas a la tabla
        if ventas:
            venta_actual = None
            productos_vendidos = ""
            for venta in ventas:
                if venta_actual is None:
                    venta_actual = venta[0]
                    productos_vendidos = f"{venta[1]} ({venta[2]}  a ${venta[3]:.2f} )"

                    total_venta = venta[3]
                    fecha = venta[4].strftime('%Y-%m-%d %H:%M:%S')  # Formatear la fecha
                elif venta[0] == venta_actual:
                    productos_vendidos += f"\n{venta[1]} ({venta[2]}  a ${venta[3]:.2f} )"

                    total_venta += venta[3]
                else:
                    data.append((venta_actual, productos_vendidos, f"${total_venta:.2f}", fecha))
                    venta_actual = venta[0]
                    productos_vendidos = f"{venta[1]} ({venta[2]}  a ${venta[3]:.2f} )"

                    total_venta = venta[3]
                    fecha = venta[4].strftime('%Y-%m-%d %H:%M:%S')  # Formatear la fecha

            # Agregar la última venta a la tabla
            data.append((venta_actual, productos_vendidos, f"${total_venta:.2f}", fecha))
        else:
            # Si no hay ventas, agregar una fila con la tabla vacía
            data.append(("", "", "", ""))

        # Crear la tabla
        tabla_ventas = Table(data, colWidths=[50, 250, 80, 80, 80, 150], repeatRows=1)

    # Estilo de la tabla
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#e0e0d1")),
            # Añadir margen a la tabla
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            # Reducir tamaño de fuente
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ])

               # Aplicar el estilo a la tabla
        tabla_ventas.setStyle(style)

        # Agregar la tabla al contenido del PDF
        elements.append(tabla_ventas)

        # Construir el PDF
        doc.build(elements)

        # Crear la respuesta con el contenido del PDF
        response = Response(buffer.getvalue())

        # Establecer el encabezado Content-Disposition para cambiar el nombre del archivo al descargarlo
        nombre_archivo = "Lista de ventas generadas Judoyeli.pdf"
        response.headers["Content-Disposition"] = f"inline; filename={nombre_archivo}"

        # Establecer el tipo de contenido como PDF
        response.headers["Content-Type"] = "application/pdf"

        return response




@app.route('/reporte-productos-caducados')
def generar_reporte_productos_caducados():
    # Realizar la consulta a la base de datos para obtener los productos caducados
    cursor.execute("""
        SELECT p.nombre, p.marca, p.precio, p.stock, c.nombre AS categoria, p.caducidad
        FROM productos p
        JOIN categorias c ON p.categoria = c.id
        WHERE p.caducidad < CURRENT_DATE() 
        ORDER BY p.nombre ASC
    """)
    productos_caducados = cursor.fetchall()

    # Crear el documento PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []


    # Agregar título al reporte
    styles = getSampleStyleSheet()
    titulo = Paragraph("Lista de productos caducados", styles['Title'])
    elements.append(titulo)

    elements.append(Spacer(1, 12))


    
    # Agregar encabezado al reporte
    encabezado = ("Nombre", "Marca", "Precio", "Stock (Kg/U)", "Categoría", "Caducidad")
    data = [encabezado] + productos_caducados
    table = Table(data, colWidths=[125, 80, 60, 46, 125, 80], repeatRows=1)

    # Estilo de la tabla
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
       ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1,colors.HexColor("#e0e0d1")),
        # Añadir margen a la tabla
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        # Reducir tamaño de fuente
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ])
    table.setStyle(style)

    # Agregar la tabla al contenido del PDF
    elements.append(table)

    # Construir el PDF
    doc.build(elements)

    # Crear la respuesta con el contenido del PDF
    response = Response(buffer.getvalue())

    # Establecer el encabezado Content-Disposition para cambiar el nombre del archivo al descargarlo
    nombre_archivo = "Lista de ventas generadas Judoyeli.pdf"
    response.headers["Content-Disposition"] = f"inline; filename={nombre_archivo}"

    # Establecer el tipo de contenido como PDF
    response.headers["Content-Type"] = "application/pdf"

    return response


@app.route('/cargar_archivo_productos', methods=['GET', 'POST'])
def cargar_archivo_productos():
    if request.method == 'POST':
        archivo = request.files['archivo_excel']
        if archivo.filename != '':
            try:
                df = pd.read_csv(archivo, encoding='ISO-8859-1')

                # Conecta a la base de datos
                connection = db
                cursor = connection.cursor()

                try:
                    # Elimina los productos existentes
                    cursor.execute("TRUNCATE TABLE productos")

                    # Itera sobre los datos y guárdalos en la base de datos
                    for index, row in df.iterrows():
                        if pd.notna(row['nombre']) and pd.notna(row['marca']) and pd.notna(row['precio']) and pd.notna(row['stock']) and pd.notna(row['categoria']) and pd.notna(row['caducidad']):
                            query = "INSERT INTO productos (nombre, marca, precio, stock, categoria, caducidad) VALUES (%s, %s, %s, %s, %s, %s)"
                            values = (row['nombre'], row['marca'], row['precio'], row['stock'], row['categoria'], row['caducidad'])
                            cursor.execute(query, values)

                    connection.commit()
                    mensaje = "¡Se importo exitosamente!"
                except Exception as e:
                    connection.rollback()
                    mensaje = f"Error al procesar el archivo: {e}"
                finally:
                    cursor.close()

                return render_template('resultado.html', mensaje=mensaje)

            except Exception as e:
                mensaje = f"Error al cargar el archivo: {e}"
                return render_template('error.html', mensaje=mensaje)

    return render_template('cargar_archivo_productos.html')

@app.route('/cargar_archivo_categorias', methods=['GET', 'POST'])
def cargar_archivo_categorias():
    if request.method == 'POST':
        archivo = request.files['archivo_excel']
        if archivo.filename != '':
            try:
                df = pd.read_csv(archivo, encoding='ISO-8859-1')

                # Conecta a la base de datos
                connection = db
                cursor = connection.cursor()

                try:
                    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
                    # Elimina las categorías existentes
                    cursor.execute("TRUNCATE TABLE categorias")

                    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

                    # Itera sobre los datos y guárdalos en la base de datos
                    for index, row in df.iterrows():
                        if pd.notna(row['id'] and pd.notna(row['nombre'])):
                            query = "INSERT INTO categorias (id, nombre) VALUES (%s, %s)"
                            values = (row['id'], row['nombre'])
                            cursor.execute(query, values)

                    connection.commit()
                    mensaje = "¡Se importo exitosamente!"
                except Exception as e:
                    connection.rollback()
                    mensaje = f"Error al procesar el archivo: {e}"
                finally:
                    cursor.close()

                return render_template('resultado2.html', mensaje=mensaje)

            except Exception as e:
                mensaje = f"Error al cargar el archivo: {e}"
                return render_template('error2.html', mensaje=mensaje)

    return render_template('cargar_archivo_categorias.html')

if __name__ == "__main__":
    app.run(debug=True)