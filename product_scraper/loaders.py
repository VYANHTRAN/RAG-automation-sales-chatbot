from scrapy.loader import ItemLoader
from itemloaders.processors import TakeFirst, MapCompose, Identity


class ProductLoader(ItemLoader):
    default_output_processor = TakeFirst()

    name_in = MapCompose(str.strip)
    url_in = MapCompose(str.strip)
    sku_in = Identity()
    productID_in = Identity()
    image_in = MapCompose(str.strip)
    price_in = Identity()
    description_in = Identity()

    main_category_in = MapCompose(str.strip)
    sub_categories_in = MapCompose(str.strip)
    specifications_in = Identity()
    variant_name_in = MapCompose(str.strip)