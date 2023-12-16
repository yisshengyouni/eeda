
import sys
import os
from web import weibo

if __name__ == '__main__':
    print('-------- start --------')
    weibo.app.run(host="0.0.0.0", port=os.getenv("PORT", default=5050), debug=True)
