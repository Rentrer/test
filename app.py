from flask import Flask,render_template, request, redirect, url_for
import pymysql
from model.forms import SearchForm
import useful_functions
import spider_modul
from config import APP_CONFIG, DB_CONFIG
import logging
import math

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log'
)

# 初始化应用
app = Flask(__name__)
app.config.update(APP_CONFIG)

def get_db_connection():
    """获取数据库连接"""
    connection = pymysql.connect(
        host=DB_CONFIG['host'], 
        user=DB_CONFIG['user'], 
        password=DB_CONFIG['password'], 
        port=DB_CONFIG['port'], 
        database=DB_CONFIG['database'],
        charset=DB_CONFIG['charset']
    )
    return connection

# 首页路由
@app.route('/')
@app.route('/index')
def index():
    # 获取分页参数 - 用于最新新闻展示
    latest_news_count = 5  # 首页显示的最新新闻数量
    
    # 每次访问首页时重新获取数据
    datalist = useful_functions.get_datalist()
    
    # 分析数据库内容
    datainfo1, string = useful_functions.get_datalist_info(datalist)
    
    # 计算 topK=8 的词汇对应的词频
    words, weights = useful_functions.get_word_weights(string, topK=8)
    
    # 获取最新新闻
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 获取最新新闻
        latest_news_sql = "SELECT * FROM guanchazhe ORDER BY publish_time DESC LIMIT %s"
        cursor.execute(latest_news_sql, (latest_news_count,))
        latest_news = cursor.fetchall()
        
        # 获取热门关键词 (按出现频率)
        hot_keywords_sql = """
        SELECT keyword, COUNT(*) as frequency 
        FROM (
            SELECT TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(key_word, ',', n.digit+1), ',', -1)) as keyword
            FROM guanchazhe
            JOIN (SELECT 0 as digit UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4) n
            ON LENGTH(REPLACE(key_word, '，', ',')) - LENGTH(REPLACE(REPLACE(key_word, '，', ','), ',', '')) >= n.digit
            WHERE key_word IS NOT NULL AND key_word != ''
        ) as keywords
        WHERE keyword != '（自动生成）' AND keyword != '自动生成' AND LENGTH(keyword) > 1
        GROUP BY keyword
        ORDER BY frequency DESC
        LIMIT 10
        """
        cursor.execute(hot_keywords_sql)
        hot_keywords = cursor.fetchall()
        
        # 获取作者统计
        authors_sql = """
        SELECT author, COUNT(*) as article_count
        FROM guanchazhe
        WHERE author IS NOT NULL AND author != ''
        GROUP BY author
        ORDER BY article_count DESC
        LIMIT 5
        """
        cursor.execute(authors_sql)
        top_authors = cursor.fetchall()
        
        cursor.close()
    finally:
        conn.close()
    
    # 传递变量给模板
    return render_template("index.html", 
                          datalist=datalist, 
                          news_info=datainfo1,
                          words=words, 
                          weights=weights,
                          latest_news=latest_news,
                          hot_keywords=hot_keywords,
                          top_authors=top_authors)


# 这里分析数据库内容，提炼出数据库信息，并对文本内容分词
datalist = useful_functions.get_datalist()
datainfo1, string = useful_functions.get_datalist_info(datalist)
# 计算 topK=8 的词汇对应的词频
words, weights = useful_functions.get_word_weights(string, topK=8)

# 首页重定位
@app.route('/temp')
def temp_page():
    return index()

# 新闻缩略页
@app.route('/news')
def news_page():
    # 获取分页和排序参数
    page = request.args.get('page', 1, type=int)  # 当前页码，默认为1
    per_page = request.args.get('per_page', 10, type=int)  # 每页显示条数，默认为10
    sort_by = request.args.get('sort', 'newest')  # 排序方式，默认为最新发布
    
    # 验证每页显示条数是否合法
    if per_page not in [10, 20, 50]:
        per_page = 10
    
    # 获取总记录数
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM guanchazhe")
        total_count = cursor.fetchone()[0]
        
        # 计算分页信息
        total_pages = math.ceil(total_count / per_page)
        
        # 确保页码有效
        if page < 1:
            page = 1
        elif page > total_pages and total_pages > 0:
            page = total_pages
        
        # 计算偏移量
        offset = (page - 1) * per_page
        
        # 根据排序方式确定SQL排序
        if sort_by == 'oldest':
            order_by = "ORDER BY publish_time ASC"
        else:  # 默认最新发布在前
            order_by = "ORDER BY publish_time DESC"
        
        # 查询当前页的数据
        sql = f"SELECT * FROM guanchazhe {order_by} LIMIT %s OFFSET %s"
        cursor.execute(sql, (per_page, offset))
        news_list = cursor.fetchall()
        
        cursor.close()
    finally:
        conn.close()
    
    # 分页和排序信息
    pagination = {
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'total_count': total_count,
        'sort': sort_by
    }
    
    return render_template("news.html", news=news_list, pagination=pagination)


# 基于词频绘制的词云
@app.route('/word')
def word_page():
    return render_template("word.html",news_info=datainfo1)


# 重定向到我的github
@app.route('/team')
def team_page():
    return redirect("https://github.com/rentrer")


# 数据库文本信息分析，topK8的词语及频率，暂时用的是直方图
@app.route('/analysis')
def analysis_page():
    # 获取词频数据
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # 这里应该是获取词频数据的查询
        # ... 查询代码 ...
        cursor.close()
    finally:
        conn.close()
    return render_template("analysis.html", words=words, weights=weights)


# 搜索界面
@app.route('/search')
def search_page():
    form = SearchForm()
    return render_template('search.html', form=form)


# 搜索结果返回界面
@app.route('/news_result', methods=['POST', 'GET'])
def newsResult_page():
    form = SearchForm()
    search = request.args.get("query", "")
    
    # 获取分页和排序参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    sort_by = request.args.get('sort', 'newest')  # 排序方式，默认为最新发布
    
    # 验证每页显示条数是否合法
    if per_page not in [10, 20, 50]:
        per_page = 10
    
    # 获取总记录数和分页数据
    search_list = []
    total_count = 0
    
    if search:
        cnn_search = get_db_connection()
        try:
            cursor_search = cnn_search.cursor()
            
            # 先查询总数
            count_sql = "SELECT COUNT(*) FROM guanchazhe WHERE content LIKE %s"
            cursor_search.execute(count_sql, ('%' + search + '%',))
            total_count = cursor_search.fetchone()[0]
            
            # 计算分页
            total_pages = math.ceil(total_count / per_page)
            if page < 1:
                page = 1
            elif page > total_pages and total_pages > 0:
                page = total_pages
                
            # 计算偏移量
            offset = (page - 1) * per_page
            
            # 根据排序方式确定SQL排序
            if sort_by == 'oldest':
                order_by = "ORDER BY publish_time ASC"
            else:  # 默认最新发布在前
                order_by = "ORDER BY publish_time DESC"
            
            # 查询分页数据
            sql_search = f"SELECT * FROM guanchazhe WHERE content LIKE %s {order_by} LIMIT %s OFFSET %s"
            cursor_search.execute(sql_search, ('%' + search + '%', per_page, offset))
            search_list = cursor_search.fetchall()
            
            cursor_search.close()
        finally:
            cnn_search.close()
    
    # 分页信息
    pagination = {
        'page': page,
        'per_page': per_page,
        'total_pages': math.ceil(total_count / per_page) if total_count > 0 else 1,
        'total_count': total_count,
        'search_query': search,  # 保存搜索词以便构建分页URL
        'sort': sort_by  # 保存排序方式
    }
    
    return render_template("news_result.html", form=form, news=search_list, pagination=pagination)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


if __name__ == "__main__":
    
    # # 启动应用
    app.run(host='0.0.0.0', port=5001, debug=True)
