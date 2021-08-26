from api_server import APIServer
import concurrent.futures
import time
import re
#LoadBalancer distributes requests to pods in Deployments
#apiServer is the apiServer
#deployment is the associated deployment
#running is the running status of the loadbalancer
#kind defines the algorithm for load balancing
#pool is the pool of threads for handling requests
class LoadBalancer:
	def __init__(self, KIND, APISERVER, DEPLOYMENT):
		self.apiServer = APISERVER
		self.deployment = DEPLOYMENT
		self.running = True
		self.kind = KIND
		self.indexArray = []
		self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=10)
	
	def __call__(self):
		
		def ThreadHandler(req, serList):
			for ser in serList:
				ms=ser.replace('(','').replace(')','')
				self.balance(req, ms)
		self.indexArray = self.deployment.msList.copy()
		for i in range (0, len(self.indexArray)):
			self.indexArray[i] = 0
		while self.running:
			self.deployment.waiting.wait()
			with self.deployment.lock:
				requests = self.deployment.pendingReqs.copy()
				self.deployment.pendingReqs.clear()
				self.deployment.waiting.clear()
				for request in requests:
					for ms in self.deployment.orderList:
						parMSList = re.split("\+",ms)
						while '' in parMSList: parMSList.remove('')
						for par in parMSList:
							serList = re.split("\.", par)
							while '' in serList: serList.remove('')
							self.pool.submit(ThreadHandler(request, serList))
					self.deployment.handledReqs.append(request)
		print("LoadBalancer Shutdown")


	def balance(self, request, MS):
		with self.apiServer.etcdLock:
			if kind == 'UA':
				#IMPLEMENT BALANCING HERE
			if kind == 'RR':

			#IMPLEMENT BALANCING HERE

			
		
