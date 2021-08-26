import threading
import time
import math
#Your Horizontal Pod Autoscaler should monitor the average resource utilization of a deployment across
#the specified time period and execute scaling actions based on this value. The period can be treated as a sliding window.
#apiServer is the apiServer
#running is the running status of the HPA
#time is the checking period for the algorithm
#deploymentLabel is the label of the associated deployment
#setPoint is the setpoint for cpu utilisation
#maxReps is the max number of pod replicas
#minReps is the minimum number of pod replicas

class HPA:
	def __init__(self, APISERVER, LOOPTIME, INFOLIST):
		self.apiServer = APISERVER
		self.running = True
		self.time = LOOPTIME
		self.deploymentLabel = INFOLIST[0]
		self.setPoint = float(INFOLIST[1])/100
		self.maxReps = 5
		self.minReps = 1
	def __call__(self):
		print('HPA Start')
		counts = 0
		while self.running:
			with self.apiServer.etcdLock:
				deployment = self.apiServer.GetDepByLabel(self.deploymentLabel)
				if deployment == None:
					self.running = False
					break
				#IMPLEMENT SCALING HERE
				
			time.sleep(self.time)
		print("HPA Shutdown")
