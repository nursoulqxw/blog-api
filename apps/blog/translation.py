from modeltranslation.translator import TranslationOptions, register

from .models import Category


@register(Category)
class CategoryTranslationOptions(TranslationOptions):
    """
    Register Category.name for translation.

    django-modeltranslation will create database columns:
        name_en, name_ru, name_kk
    and make `category.name` return the value for the currently active
    language automatically.  No changes are needed in the serializer.
    """

    fields = ("name",)