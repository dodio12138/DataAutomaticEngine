"""爬虫主入口：可被 scheduler 调用或直接执行。"""
from services.panda.fetch_orders import HungryPandaScraper
import datetime


def main(start_date: str = None, end_date: str = None):
    # 默认使用“昨天 - 今天”的时间范围
    if not start_date or not end_date:
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        start_date = yesterday.strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')

    scraper = HungryPandaScraper("海底捞冒菜（塔桥）", start_date, end_date)
    scraper.run()


if __name__ == "__main__":
    main()
