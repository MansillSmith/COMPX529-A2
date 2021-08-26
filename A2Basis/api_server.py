from deployment import Deployment
from microservice import Microservice
from end_point import EndPoint
from etcd import Etcd
from pod import Pod
from request import Request
from worker_node import WorkerNode
import threading
import random
import copy
import re

#The APIServer handles the communication between controllers and the cluster. It houses
#the methods that can be called for cluster management

class APIServer:
	def __init__(self):
		self.etcd = Etcd()
		self.etcdLock = threading.Lock()
		self.requestWaiting = threading.Event()
	
	
# CreateWorker creates a WorkerNode from a list of arguments and adds it to the etcd nodeList
	def CreateWorker(self, info):
		worker = WorkerNode(info)
		self.etcd.nodeList.append(worker)

		
# CreateDeployment creates a Deployment object from a list of arguments and adds it to the etcd deploymentList
	def CreateDeployment(self, info):
		deployment = Deployment(info)
		self.etcd.deploymentList.append(deployment)
		mslist = re.split("\+|\.|\(|\)", deployment.msPath)
		while '' in mslist: mslist.remove('')
		deployment.msList = mslist
		for ms in deployment.msList:
			for msTemplate in self.etcd.microserviceTemplates:
				if msTemplate.microserviceLabel == ms:
					depMS = copy.copy(msTemplate)
					depMS.deploymentLabel = deployment.deploymentLabel
					self.etcd.microserviceList.append(depMS)


#CreateMicroserviceTemplate creates a Microservice template object from a list of arguments and stores it in etcd.
	def CreateMicroserviceTemplate(self, info):
		microservice = Microservice(info)
		self.etcd.microserviceTemplates.append(microservice)

# CreateEndpoint creates an EndPoint object using information from a provided Pod and Node and appends it 
# to the endPointList in etcd
	def CreateEndPoint(self, pod, worker):
		endPoint = EndPoint(pod, pod.deploymentLabel, pod.microserviceLabel, worker)
		self.etcd.endPointList.append(endPoint)

# 	GetDeployments method returns the list of deployments stored in etcd 	
	def GetDeployments(self):
		return self.etcd.deploymentList.copy()
		
#	GetWorkers method returns the list of WorkerNodes stored in etcd
	def GetWorkers(self):
		return self.etcd.nodeList.copy()
		
#	GetPending method returns the list of PendingPods stored in etcd
	def GetPending(self):
		return self.etcd.pendingPodList.copy()
		
#	GetEndPoints method returns the list of EndPoints stored in etcd
	def GetEndPoints(self):
		return self.etcd.endPointList.copy()
				
# GetEndPointsByLabel returns a list of EndPoints associated with a given deployment
	def GetEndPointsByLabel(self, deploymentLabel, microserviceLabel):
		endPoints = []
		for endPoint in self.etcd.endPointList:
			if endPoint.deploymentLabel == deploymentLabel:
				if endPoint.microserviceLabel == microserviceLabel:
					endPoints.append(endPoint)
		return endPoints

#GetDepByLabel returns the Deployment object associated with a deploymentLabel:
	def GetDepByLabel(self, deploymentLabel):
		deployments = list(filter(lambda x: x.deploymentLabel == deploymentLabel, self.etcd.deploymentList))
		if len(deployments) == 1:
			return deployments[0]
		else:
			print('Deployment '+deploymentLabel+' not found')

#GetMSByLabel returns the Microservice object associated with a microserviceLabel and a deploymentLabel:
	def GetMSByLabel(self, msLabel, depLabel):
		microservices = list(filter(lambda x: x.microserviceLabel == msLabel, filter(lambda x: x.deploymentLabel == depLabel, self.etcd.microserviceList)))
		if len(microservices) == 1:
			return microservices[0]
		else:
			print('MS '+ msLabel+' DEP '+depLabel+' not found')

#RemoveEndPoint removes the EndPoint from the list within etcd
	def RemoveEndPoint(self, endPoint):
		endPoint.node.available_cpu+=endPoint.pod.assigned_cpu
		self.etcd.endPointList.remove(endPoint)

# RemoveDeployment deletes the associated Deployment object from etcd and sets the status of all associated pods to 'TERMINATING'
	def RemoveDeployment(self, info):
		for ms in self.etcd.microserviceList:
			if ms.deploymentLabel == info[0]:
				ms.expectedReplicas = 0
		dep = self.GetDepByLabel(info[0])
		dep.waiting.set()

#GeneratePodName creates a random label for a pod
	def GeneratePodName(self):
		label = random.randint(111,999)
		for pod in self.etcd.runningPodList:
			if pod.podName == label:
				label = self.GeneratePodName()
		for pod in self.etcd.pendingPodList:
			if pod.podName == label:
				label = self.GeneratePodName()
		return label


# CreatePod finds the resource allocations associated with a deployment and creates a pod using those metrics
	def CreatePod(self, microservice):
		podName = microservice.microserviceLabel + "_" + str(self.GeneratePodName())
		pod = Pod(podName, microservice.cpuCost, microservice.deploymentLabel, microservice.microserviceLabel, microservice.handlingTime)
		self.etcd.pendingPodList.append(pod)
		
# GetPod returns the pod object associated with an EndPoint
	def GetPod(self, endPoint):
		if endPoint.pod == None:
			print("No Pod Found")
		else:
			return endPoint.pod

#TerminatePod gracefully shuts down a Pod
	def TerminatePod(self, endPoint):
		pod = endPoint.pod
		pod.status="TERMINATING"
		self.RemoveEndPoint(endPoint)


# CrashPod finds a pod from a given deployment and sets its status to 'FAILED'
# Any resource utilisation on the pod will be reset to the base 0
	def CrashPod(self, info):
		dep = self.GetDepByLabel(info[0])
		ms = random.choice(dep.msList)
		endPoints = self.GetEndPointsByLabel(info[0], ms)
		if len(endPoints) == 0:
			print("No Pods to crash")
		else:
			pod = self.GetPod(endPoints[0])
			pod.status = "FAILED"
			pod.crash.set()

#	Alter these method so that the requests are pushed to Deployments instead of etcd
	def PushReq(self, info):
		self.etcd.reqCreator.submit(self.ReqPusher, info)


	def ReqPusher(self, info):
			deployment = self.GetDepByLabel(info[1])
			with deployment.lock:
				deployment.pendingReqs.append(Request(info))
				deployment.waiting.set()
		
