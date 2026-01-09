"""
Product Store Service with UI
"""
from decimal import Decimal

from flask import jsonify, request, abort
from flask import url_for  # noqa: F401 pylint: disable=unused-import

from service.models import Product, Category, DataValidationError
from service.common import status  # HTTP Status Codes
from . import app


######################################################################
#  U T I L I T Y   F U N C T I O N S
######################################################################
def check_content_type(content_type):
    """Checks that the media type is correct"""
    if "Content-Type" not in request.headers:
        app.logger.error("No Content-Type specified.")
        abort(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Content-Type must be {content_type}",
        )

    if request.headers["Content-Type"] == content_type:
        return

    app.logger.error("Invalid Content-Type: %s", request.headers["Content-Type"])
    abort(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        f"Content-Type must be {content_type}",
    )


def _parse_bool_param(value: str):
    """Parse a boolean query parameter into True/False or return None if invalid."""
    if value is None:
        return None
    val = value.strip().lower()
    if val in ("true", "1", "yes", "y", "t"):
        return True
    if val in ("false", "0", "no", "n", "f"):
        return False
    return None


def _get_product_or_404(product_id: int) -> Product:
    """Helper to fetch a product by id or abort with 404."""
    product = Product.find(product_id)
    if not product:
        abort(status.HTTP_404_NOT_FOUND, f"Product with id '{product_id}' was not found.")
    return product

######################################################################
# H E A L T H   C H E C K
######################################################################
@app.route("/health")
def healthcheck():
    """Let them know our heart is still beating"""
    return jsonify(status=200, message="OK"), status.HTTP_200_OK


######################################################################
# H O M E   P A G E
######################################################################
@app.route("/")
def index():
    """Base URL for our service"""
    return app.send_static_file("index.html")



######################################################################
# C R E A T E   A   N E W   P R O D U C T
######################################################################
@app.route("/products", methods=["POST"])
def create_products():
    """
    Creates a Product
    This endpoint will create a Product based the data in the body that is posted
    """
    app.logger.info("Request to Create a Product...")
    check_content_type("application/json")

    data = request.get_json()
    app.logger.info("Processing: %s", data)
    product = Product()
    try:
        product.deserialize(data)
    except DataValidationError as error:
        abort(status.HTTP_400_BAD_REQUEST, str(error))

    product.create()
    app.logger.info("Product with new id [%s] saved!", product.id)

    message = product.serialize()
    location_url = url_for("get_products", product_id=product.id, _external=True)
    return jsonify(message), status.HTTP_201_CREATED, {"Location": location_url}


######################################################################
# L I S T   A L L   P R O D U C T S
######################################################################
@app.route("/products", methods=["GET"])
def list_products():
    """Returns all Products (optionally filtered by name, category, available)"""
    app.logger.info("Request to list Products...")

    name = request.args.get("name")
    category = request.args.get("category")
    available = request.args.get("available")

    # Filter by name (optional)
    if name:
        products = Product.find_by_name(name).all()

    # Filter by category (optional)
    elif category:
        try:
            category_enum = getattr(Category, category)
        except AttributeError:
            abort(status.HTTP_400_BAD_REQUEST, f"Invalid category: {category}")
        products = Product.find_by_category(category_enum).all()

    # Filter by availability (optional)
    elif available is not None:
        bool_value = _parse_bool_param(available)
        if bool_value is None:
            abort(status.HTTP_400_BAD_REQUEST, f"Invalid availability: {available}")
        products = Product.find_by_availability(bool_value).all()

    # No filter -> return all products
    else:
        products = Product.all()

    results = [product.serialize() for product in products]
    return jsonify(results), status.HTTP_200_OK


######################################################################
# R E A D   A   P R O D U C T
######################################################################
@app.route("/products/<int:product_id>", methods=["GET"])
def get_products(product_id):
    """Retrieve a single Product by id"""
    app.logger.info("Request to Retrieve Product with id [%s]", product_id)
    product = _get_product_or_404(product_id)
    return jsonify(product.serialize()), status.HTTP_200_OK


######################################################################
# U P D A T E   A   P R O D U C T
######################################################################
@app.route("/products/<int:product_id>", methods=["PUT"])
def update_products(product_id):
    """Update an existing Product"""
    app.logger.info("Request to Update Product with id [%s]", product_id)
    check_content_type("application/json")

    product = _get_product_or_404(product_id)
    data = request.get_json()

    try:
        product.deserialize(data)
    except DataValidationError as error:
        abort(status.HTTP_400_BAD_REQUEST, str(error))

    # Ensure the id is not changed by request payload
    product.id = product_id
    product.update()
    return jsonify(product.serialize()), status.HTTP_200_OK


######################################################################
# D E L E T E   A   P R O D U C T
######################################################################
@app.route("/products/<int:product_id>", methods=["DELETE"])
def delete_products(product_id):
    """Delete a Product"""
    app.logger.info("Request to Delete Product with id [%s]", product_id)
    product = _get_product_or_404(product_id)
    product.delete()
    return "", status.HTTP_204_NO_CONTENT
