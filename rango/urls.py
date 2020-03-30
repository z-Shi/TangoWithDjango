from django.urls import path
from rango.views import AboutView, AddCategoryView, IndexView, ShowCategoryView, AddPageView, RestrictedView, \
    GotoUrlView, RegisterProfileView, ProfileView, ListProfilesView, LikeCategoryView, CategorySuggestionView, \
    SearchAddPageView


app_name = 'rango'

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('about/', AboutView.as_view(), name='about'),
    path('category/<slug:category_name_slug>/', ShowCategoryView.as_view(), name='show_category'),
    path('add_category/', AddCategoryView.as_view(), name='add_category'),
    path('category/<slug:category_name_slug>/add_page/', AddPageView.as_view(), name='add_page'),
    path('restricted/', RestrictedView.as_view(), name='restricted'),
    path('goto/', GotoUrlView.as_view(), name='goto'),
    path('register_profile/', RegisterProfileView.as_view(), name='register_profile'),
    path('profile/<username>/', ProfileView.as_view(), name='profile'),
    path('profiles/', ListProfilesView.as_view(), name='list_profiles'),
    path('like_category/', LikeCategoryView.as_view(), name='like_category'),
    path('suggest/', CategorySuggestionView.as_view(), name='suggest'),
    path('search_add_page/', SearchAddPageView.as_view(), name='search_add_page'),
]
