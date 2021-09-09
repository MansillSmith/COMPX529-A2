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
			endpointList = self.apiServer.GetEndPointsByLabel(self.deployment.deploymentLabel, MS)
			if len(endpointList) > 0:
				if self.kind == 'UA':
					#IMPLEMENT BALANCING HERE
					#utilisation aware
					#look at all the active pod replicas
					#util = number of threads being used / thread pool
					#keeps utilisation consistent accross pods

					#Get all the microservice associated with this deployment
					# for microserviceLabel in self.deployment.mslist:
						#microservice = self.apiServer.GetMSByLabel(microserviceLabel, self.deployment.deploymentLabel)
						#get every end point for the microservice
					# endpointList = self.apiServer.GetEndPointsByLabel(self.deployment.deploymentLabel, MS)
					# if len(endpointList) > 0:
					#get the current cpu util of each pod
					#find the lowest util
					lowestUtilPod = None
					for endpoint in endpointList:
						if lowestUtilPod is None or (endpoint.pod.available_cpu / endpoint.pod.assigned_cpu) < (lowestUtilPod.available_cpu / lowestUtilPod.assigned_cpu):
							lowestUtilPod = endpoint.pod

					#handle request on that pod
					lowestUtilPod.HandleRequest(request)
				if self.kind == 'RR':
					# If there were three pods
					# req 1 -> 1, req 2 -> 2, req 3 -> 3, req 4 -> 1 ...
					# for microservicelabel in self.deployment.mslist:
					microservice = self.apiServer.GetMSByLabel(MS, self.deployment.deploymentLabel)
					# endpointList = self.apiServer.GetEndPoint(self.deployment.deploymentLabel, MS)

					# if len(endpointList) > 0:
					chosenPod = None
					for endpoint in endpointList:
						if endpoint.pod.podName not in microservice.RRMemory:
							chosenPod = endpoint.pod
							break

					if len(microservice.RRMemory) == 0 or chosenPod is None:
						chosenPod = endpointList[0].pod

					microservice.RRMemory.append(chosenPod.podName)

					chosenPod.HandleRequest(request)
			#IMPLEMENT BALANCING HERE

			
		
