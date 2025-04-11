import pymysql
import jieba
import jieba.analyse
import os
from config import DB_CONFIG  # 导入数据库配置
import math

# 设置jieba的日志级别
jieba.setLogLevel(20)  # 设置为INFO级别，减少不必要的输出


# 加载停用词函数 - 从word_cloud.py复制过来
def load_stop_words(file_path='./static/stop_words.txt'):
    """加载停用词"""
    stop_words = set()
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    stop_words.add(line.strip())
        else:
            print(f"警告: 停用词文件不存在: {file_path}")
    except Exception as e:
        print(f"加载停用词异常: {str(e)}")
    
    # 添加一些常见但无意义的词
    common_stop_words = {
        '的', '了', '是', '在', '我们', '你们', '他们', '有', '和', '就', '也',
        '可能', '表示', '一个', '这个', '那个', '就是', '因为', '所以', 
        '但是', '然后', '如果', '这样', '那样', '出现', '进行', '这种', 
        '一些', '这些', '那些', '没有', '什么', '自己', '目前', '为了',
        '他们', '我们', '你们', '认为', '觉得', '知道', '需要', '应该'
    }
    stop_words.update(common_stop_words)
    
    return stop_words

# 连接数据库并提取数据库内容
def get_datalist():
    """获取所有新闻数据"""
    try:
        # 每次调用都重新连接数据库，确保获取最新数据
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = 'SELECT * FROM guanchazhe ORDER BY Id DESC'  # 按ID倒序排列，最新的新闻在前面
        cursor.execute(sql)
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        
        print(f"从数据库加载了 {len(result)} 条新闻")
        return result
    except Exception as e:
        print(f"获取新闻数据异常: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return []


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


# 对数据库文本内容进行分词，并返回 data_info = [新闻数，词云数，词汇数，作者人数] ->首页展示的三个内容
def get_datalist_info(datalist):
    """获取数据统计信息和分词结果"""
    if not datalist:
        return [0, 0, 0, 0], ""
    
    # 合并所有新闻内容
    text = "".join(item[4] for item in datalist if item[4])

    # 分词，提高效率
    words = jieba.lcut(text)  # 使用lcut代替cut，直接返回列表而不是生成器
    string = ' '.join(words)
    
    # 统计数据
    authors = set(item[2] for item in datalist if item[2])
    data_info = [len(datalist), 1, len(string), len(authors)]
    return data_info, string


# 对输入文本进行分词，并返回词汇权重
def get_word_weights(string, topK=10):
    """提取关键词及其权重
    
    Args:
        string: 要分析的文本
        topK: 返回前K个关键词
        
    Returns:
        words: 关键词列表
        weights: 权重列表
    """
    if not string:
        return [], []
    
    # 加载停用词列表
    stop_words = load_stop_words()
    
    # 使用TF-IDF算法提取关键词 - 比TextRank更适合提取新闻关键词
    results = jieba.analyse.extract_tags(
        string, 
        withWeight=True, 
        topK=topK * 3,  # 提取更多候选词，以便过滤后仍有足够的词
        allowPOS=('ns', 'n', 'nr', 'nt', 'nz')  # 只保留地名、人名、名词、机构名等实体词
    )
    
    # 过滤停用词
    filtered_results = [(word, weight) for word, weight in results 
                        if word not in stop_words and len(word) >= 2]
    
    # 取前topK个
    filtered_results = filtered_results[:topK]
    
    # 分离关键词和权重
    words, weights = [], []
    if filtered_results:
        words, weights = zip(*filtered_results)
        
        # 归一化权重值到0-1区间，便于可视化
        max_weight = max(weights)
        weights = [w/max_weight for w in weights]
    
    return list(words), list(weights)


# 文本关键字提取优化
def get_keyword_from_content(content, keyword_count=5):
    """从内容中提取关键词
    
    Args:
        content: 文本内容
        keyword_count: 需要提取的关键词数量
        
    Returns:
        keywords_str: 关键词字符串，用逗号分隔
    """
    if not content:
        return "无关键词"
    
    # 加载停用词列表
    stop_words = load_stop_words()
    
    # 使用TF-IDF算法提取关键词
    all_keywords = jieba.analyse.extract_tags(
        content, 
        topK=keyword_count * 3,  # 提取更多候选词，以便过滤后仍有足够的词
        withWeight=False,
        allowPOS=('ns', 'n', 'nr', 'nt', 'nz', 'vn')  # 包含地名、人名、名词、机构名、名动词
    )
    
    # 过滤停用词和短词
    keywords = [word for word in all_keywords 
               if word not in stop_words 
               and len(word) >= 2 
               and not word.isdigit()][:keyword_count]
    
    if not keywords:
        return "无关键词（自动生成）"
    
    # 返回关键词字符串
    return ", ".join(keywords) + "（自动生成）"

# 获取分页新闻数据
def get_paginated_datalist(page=1, per_page=10):
    """获取分页后的新闻数据
    
    Args:
        page: 页码，从1开始
        per_page: 每页记录数
        
    Returns:
        news_list: 当前页的新闻列表
        pagination: 分页信息字典
    """
    try:
        # 连接数据库
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取总记录数
        cursor.execute("SELECT COUNT(*) FROM guanchazhe")
        total_count = cursor.fetchone()[0]
        
        # 计算总页数
        total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1
        
        # 确保页码有效
        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages
            
        # 计算偏移量
        offset = (page - 1) * per_page
        
        # 查询当前页的数据
        sql = "SELECT * FROM guanchazhe ORDER BY Id DESC LIMIT %s OFFSET %s"
        cursor.execute(sql, (per_page, offset))
        news_list = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # 构建分页信息
        pagination = {
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_count': total_count
        }
        
        return news_list, pagination
        
    except Exception as e:
        print(f"获取分页新闻数据异常: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return [], {'page': 1, 'per_page': per_page, 'total_pages': 1, 'total_count': 0}
