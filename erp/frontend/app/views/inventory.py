"""
Inventory Views
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from app import api_request, login_required

bp = Blueprint('inventory', __name__, url_prefix='/inventory')


# ==================== CATEGORIES ====================

@bp.route('/categories')
@login_required
def list_categories():
    """List all categories"""
    categories, status = api_request('GET', '/inventory/categories')
    
    if status != 200:
        categories = []
    
    return render_template('inventory/categories.html', title='Categories', categories=categories)


@bp.route('/categories/new', methods=['POST'])
@login_required
def create_category():
    """Create new category"""
    data = {
        'name': request.form.get('name'),
        'description': request.form.get('description', '')
    }
    
    response, status = api_request('POST', '/inventory/categories', data=data)
    
    if status == 200:
        if request.headers.get('HX-Request'):
            return render_template('inventory/partials/category_row.html', category=response)
        flash('Category created', 'success')
        return redirect(url_for('inventory.list_categories'))
    
    error = response.get('detail', 'Failed to create category') if response else 'Failed'
    return render_template('shared/partials/error_alert.html', error=error)


@bp.route('/categories/<int:category_id>/edit', methods=['GET', 'PUT'])
@login_required
def edit_category(category_id):
    """Edit category"""
    if request.method == 'GET':
        category, status = api_request('GET', f'/inventory/categories/{category_id}')
        if status != 200:
            return 'Category not found', 404
        return render_template('inventory/partials/category_row_edit.html', category=category)
    
    # PUT
    data = {
        'name': request.form.get('name'),
        'description': request.form.get('description', '')
    }
    
    response, status = api_request('PUT', f'/inventory/categories/{category_id}', data=data)
    
    if status == 200:
        return render_template('inventory/partials/category_row.html', category=response)
    
    return render_template('shared/partials/error_alert.html', error='Failed to update')


@bp.route('/categories/<int:category_id>', methods=['GET'])
@login_required
def get_category(category_id):
    """Get single category row"""
    category, status = api_request('GET', f'/inventory/categories/{category_id}')
    if status != 200:
        return 'Not found', 404
    return render_template('inventory/partials/category_row.html', category=category)


@bp.route('/categories/<int:category_id>/delete', methods=['DELETE'])
@login_required
def delete_category(category_id):
    """Delete category"""
    response, status = api_request('DELETE', f'/inventory/categories/{category_id}')
    
    if status == 200:
        return ''
    
    return jsonify({'error': 'Cannot delete category with products'}), 400


# ==================== PRODUCTS ====================

@bp.route('/products')
@login_required
def list_products():
    """List all products"""
    products, status = api_request('GET', '/inventory/products')
    categories, _ = api_request('GET', '/inventory/categories')
    
    if status != 200:
        products = []
    
    return render_template('inventory/products.html', title='Products', products=products, categories=categories or [])


@bp.route('/products/low-stock')
@login_required
def low_stock():
    """List low stock products"""
    products, status = api_request('GET', '/inventory/products/low-stock')
    
    if status != 200:
        products = []
    
    return render_template('inventory/low_stock.html', title='Low Stock', products=products)


@bp.route('/products/new', methods=['GET', 'POST'])
@login_required
def new_product():
    """Create new product"""
    if request.method == 'GET':
        categories, _ = api_request('GET', '/inventory/categories')
        return render_template('inventory/product_form.html', 
                              title='New Product', 
                              product=None,
                              categories=categories or [])
    
    # POST
    data = {
        'name': request.form.get('name'),
        'sku': request.form.get('sku'),
        'description': request.form.get('description'),
        'unit': request.form.get('unit'),
        'purchase_price': request.form.get('purchase_price', 0),
        'sales_price': request.form.get('sales_price', 0),
        'opening_stock': request.form.get('opening_stock', 0),
        'reorder_level': request.form.get('reorder_level', 0),
        'category_id': request.form.get('category_id')
    }
    
    response, status = api_request('POST', '/inventory/products', data=data)
    
    if status == 200:
        flash('Product created', 'success')
        return redirect(url_for('inventory.list_products'))
    
    error = response.get('detail', 'Failed to create product') if response else 'Failed'
    categories, _ = api_request('GET', '/inventory/categories')
    return render_template('inventory/product_form.html', 
                          title='New Product',
                          product=None,
                          categories=categories or [],
                          error=error)


@bp.route('/products/<int:product_id>')
@login_required
def view_product(product_id):
    """View product details"""
    product, status = api_request('GET', f'/inventory/products/{product_id}')
    
    if status != 200:
        flash('Product not found', 'error')
        return redirect(url_for('inventory.list_products'))
    
    return render_template('inventory/product_detail.html', title=product.get('name', 'Product'), product=product)


@bp.route('/products/<int:product_id>/edit', methods=['GET', 'PUT'])
@login_required
def edit_product(product_id):
    """Edit product"""
    if request.method == 'GET':
        product, status = api_request('GET', f'/inventory/products/{product_id}')
        categories, _ = api_request('GET', '/inventory/categories')
        if status != 200:
            return 'Product not found', 404
        return render_template('inventory/partials/product_row_edit.html', product=product, categories=categories or [])
    
    # PUT
    data = {k: v for k, v in request.form.items() if k != 'csrf_token'}
    
    response, status = api_request('PUT', f'/inventory/products/{product_id}', data=data)
    
    if status == 200:
        return render_template('inventory/partials/product_row.html', product=response)
    
    return render_template('shared/partials/error_alert.html', error='Failed to update')


@bp.route('/products/<int:product_id>/delete', methods=['DELETE'])
@login_required
def delete_product(product_id):
    """Delete product"""
    response, status = api_request('DELETE', f'/inventory/products/{product_id}')
    
    if status == 200:
        return ''
    
    return jsonify({'error': 'Failed to delete product'}), 400


@bp.route('/products/<int:product_id>/adjust-stock', methods=['POST'])
@login_required
def adjust_stock(product_id):
    """Adjust product stock"""
    data = {
        'quantity_change': request.form.get('quantity_change'),
        'reason': request.form.get('reason')
    }
    
    response, status = api_request('POST', f'/inventory/products/{product_id}/adjust-stock', data=data)
    
    if status == 200:
        return render_template('inventory/partials/product_row.html', product=response)
    
    error = response.get('detail', 'Failed to adjust stock') if response else 'Failed'
    return render_template('shared/partials/error_alert.html', error=error)


@bp.route('/stock-adjustments')
@login_required
def stock_adjustments():
    """View stock adjustment history"""
    return render_template('inventory/stock_adjustments.html', title='Stock Adjustments')
