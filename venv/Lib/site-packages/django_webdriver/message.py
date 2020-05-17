class Message(object):
	@staticmethod
	def _build_msg(color, msg):
		return '{color}{msg}\x1b[0m'.format(color=color, msg=msg)

	@classmethod
	def build_error(cls, msg):
		return cls._build_msg('\x1b[31m', msg)

	@classmethod
	def build_warning(cls, msg):
		return cls._build_msg('\x1b[33m', msg)	
