from datetime import datetime

def log(content, show_time=False):
	now = datetime.now()
	path = 'logs/{}.{}.{}.log'.format(now.year, now.month, now.day)
	with open(path, 'a') as file:
		data = '[{}:{}:{}] {}\n'.format(now.hour, now.minute, now.second, content)
		file.write(data)
		if not show_time: print(content)
		else: print(data)
	return