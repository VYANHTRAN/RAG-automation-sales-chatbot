import scrapy


class ProductItem(scrapy.Item):
    name = scrapy.Field()
    url = scrapy.Field()
    sku = scrapy.Field()
    productID = scrapy.Field()
    image = scrapy.Field()
    price = scrapy.Field()
    description = scrapy.Field()
    main_category = scrapy.Field()
    sub_categories = scrapy.Field()
    variant_name = scrapy.Field()