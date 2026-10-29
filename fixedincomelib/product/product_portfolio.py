"""The template's weighted product container, also used to hold a stream."""

from fixedincomelib.product.product_interfaces import Product, ProductBuilderRegistry


class ProductPortfolio(Product):
    _version = 1
    _product_type = "PRODUCT_PORTFOLIO"

    def __init__(self, products, weights=None):
        super().__init__()
        if weights is None:
            weights = [1.0] * len(products)
        self.elements_ = list(zip(products, weights))
        self.num_elements_ = len(products)
        self.first_date_ = min(p.first_date for p in products)
        self.last_date_ = max(p.last_date for p in products)
        self.currency_ = list(dict.fromkeys(p.currency for p in products))
        self.notional_ = sum(p.notional * w for p, w in self.elements_)
        self.long_or_short_ = [p.long_or_short for p in products]

    @property
    def num_elements(self):
        return self.num_elements_

    @property
    def num_elemnts(self):
        """Retain the template's accessor spelling."""
        return self.num_elements_

    def element(self, i):
        return self.elements_[i][0]

    def weight(self, i):
        return self.elements_[i][1]

    def accept(self, visitor):
        return visitor.visit(self)

    def serialize(self):
        return {
            "VERSION": self._version, "TYPE": self._product_type,
            "PRODUCTS": [p.serialize() for p, _ in self.elements_],
            "WEIGHTS": [w for _, w in self.elements_],
        }

    @classmethod
    def deserialize(cls, content):
        products = [ProductBuilderRegistry().get(p["TYPE"] + "_DES")(p)
                    for p in content["PRODUCTS"]]
        return cls(products, content["WEIGHTS"])


ProductBuilderRegistry().register(ProductPortfolio._product_type + "_DES", ProductPortfolio.deserialize)
