$(document).ready(function() {
    $('#like_btn').click(function() {
        var catecategoryIdVar;
        catecategoryIdVar = $(this).attr('data-categoryid');

        $.get('/rango/like_category/',
            {'category_id': catecategoryIdVar},
            function(data) {
                $('#like_count').html(data);
                $('#like_btn').hide();
            })
    });

    $('#search-input').keyup(function() {
        var query;
        query = $(this).val();
        $.get('/rango/suggest/',
            {'suggestion': query},
            function(data) {
                $('#categories-listing').html(data);
            })
    });

    $('.add_page_btn').click(function() {
        var categoryId = $(this).attr('data-categoryid');
        var title = $(this).attr('data-title');
        var url = $(this).attr('data-url');
        var btn = $(this)

        $.get('/rango/search_add_page/',
            {'categoryId': categoryId, 'title': title, 'url': url},
            function(data) {
                $('#page-list').html(data);
                btn.hide();
            })
    })
});
