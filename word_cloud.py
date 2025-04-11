# import jieba        #分词
from matplotlib import pyplot as plt    #绘图，数据可视化
from wordcloud import WordCloud         #词云
from PIL import Image                   #图片处理
import numpy as np                      #矩阵运算
import pymysql                          #数据库
import jieba.analyse
import re
import os
from config import DB_CONFIG  # 导入数据库配置

# 设置jieba的日志级别
jieba.setLogLevel(20)  # 设置为INFO级别，减少不必要的输出

def get_news_content():
    """从数据库获取新闻内容"""
    datalist = []
    
    try:
        # 使用导入的配置信息
        conn = pymysql.connect(
            host=DB_CONFIG['host'], 
            user=DB_CONFIG['user'], 
            password=DB_CONFIG['password'], 
            port=DB_CONFIG['port'], 
            database=DB_CONFIG['database'],
            charset=DB_CONFIG['charset']
        )
        cursor = conn.cursor()
        sql = 'SELECT * FROM guanchazhe'
        cursor.execute(sql)
        datalist = cursor.fetchall()
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"获取新闻数据异常: {str(e)}")
    
    return datalist

def preprocess_text(text):
    """预处理文本数据"""
    # 移除URL - 修复正则表达式
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+\']|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    # 注意这里将 \( 改为 \\(，正确转义括号
    
    # 移除标点符号
    text = re.sub(r'[^\w\s]', '', text)
    # 移除数字
    text = re.sub(r'\d+', '', text)
    return text

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
    common_stop_words = {'的', '了', '是', '在', '我们', '你们', '他们', '有', '和', '就', '也'}
    stop_words.update(common_stop_words)
    
    return stop_words

def generate_wordcloud():
    """生成高清词云"""
    # 获取数据
    datalist = get_news_content()
    
    if not datalist:
        print("没有获取到数据，无法生成词云")
        return
    
    # 提取并合并所有新闻内容
    text = " ".join(item[4] for item in datalist if item[4])
    
    # 预处理文本
    text = preprocess_text(text)
    
    # 加载停用词
    stop_words = load_stop_words()
    
    # 分词
    words = jieba.lcut(text)
    
    # 过滤停用词和短词
    filtered_words = [
        word for word in words
        if word not in stop_words
        and len(word) >= 2
        and not word.isdigit()  # 过滤纯数字
    ]
    
    if not filtered_words:
        print("过滤后没有剩余词语，无法生成词云")
        return
    
    # 检查图片路径是否存在
    img_path = './static/assets/img/tree.jpg'
    if not os.path.exists(img_path):
        print(f"警告: 词云形状图片不存在: {img_path}")
        # 如果图片不存在，使用None作为mask
        img_array = None
    else:
        # 打开遮罩图片并转换为数组
        # 增加图片大小和质量
        img = Image.open(img_path)
        # 可选：放大原始图片以提高清晰度
        img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
        img_array = np.array(img)
    
    # 检查字体路径是否存在
    font_path = "./static/simhei.ttf"
    if not os.path.exists(font_path):
        print(f"警告: 指定字体不存在: {font_path}")
        font_path = None  # 使用默认字体
    
    # 创建高清词云对象
    wc = WordCloud(
        background_color='white',
        mask=img_array,
        font_path=font_path,
        max_words=150,           # 适当减少词数以增加清晰度
        max_font_size=150,       # 增加字体最大值
        min_font_size=10,        # 设置最小字体大小
        random_state=42,         # 随机状态，保证可复现性
        collocations=False,      # 避免词语重复
        width=1600,              # 增加词云宽度
        height=1200,             # 增加词云高度
        scale=2,                 # 增加缩放因子，提高清晰度
        prefer_horizontal=0.9    # 大部分词语水平显示
    )
    
    # 生成词云
    wc.generate(' '.join(filtered_words))
    
    # 保存词云图片
    output_path = './static/assets/img/key_word.png'
    
    try:
        # 直接保存WordCloud生成的图片
        wc.to_file(output_path)
        print(f"词云图片已直接保存至: {output_path}")
        
        # 使用matplotlib方式保存，移除不支持的参数
        plt.figure(figsize=(20, 16), dpi=300)  # 大幅增加图像大小和DPI
        plt.imshow(wc, interpolation='lanczos')  # 使用高质量插值
        plt.axis('off')  # 不显示坐标轴
        
        # 确保目录存在
        os.makedirs(os.path.dirname('./static/assets/img/key_word_hd.png'), exist_ok=True)
        # 另存一个高清版本，移除不支持的optimize参数
        plt.savefig('./static/assets/img/key_word_hd.png', 
                   dpi=600,               # 提高DPI到600
                   bbox_inches='tight',   # 紧凑布局
                   pad_inches=0.1,        # 减少边距
                   format='png',          # 确保使用PNG格式
                   transparent=False)     # 不透明背景
                   # 移除optimize参数
                   
        print(f"高清词云图片已保存至: ./static/assets/img/key_word_hd.png")
        
    except Exception as e:
        print(f"保存词云图片时发生错误: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    generate_wordcloud()

















