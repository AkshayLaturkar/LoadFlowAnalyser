'''
Load FLow Analyser
Copyright (C) 2020 Akshay Arvind Laturkar

Date Created : 25 March 2020 -- Version 1.0.0

This program is free software: you can redistribute it
and/or modify it under the terms of the GNU General
Public License as published by the Free Software
Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be
useful, but WITHOUT ANY WARRANTY; without even the
implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public
License along with this program.
If not, see <https://www.gnu.org/licenses/>.
'''


import numpy as np;
from collections import Counter;

class LoadFlow:
    
    '''
    N is no. of Buses
    P is Nx1 Matrix
    Q is Nx4 Matrix as Q,Qmin,Qmax,Qd
    V is Nx3 Matrix as V,Vmin,Vmax
    BT is Nx1 Matrix for Bus Type
    YBus is NxN Matrix
    MaxIter is Max. No. of Iterations
    Vlimit is True if limits are enabled
    Qlimit is True if limits are disabled
    Line is Lx4 Matrix as LNo,From Bus,To Bus,B/2
    '''
    def __init__(self,N,P,Q,V,BT,YBus,MaxIter,Vlimit,Qlimit,Line):
        self.n = N;
        self.BT = np.array(BT).reshape((N,1)).copy();
        self.P = np.array(P).reshape((N,1)).copy();
        self.Q = np.array(Q).reshape((N,4)).copy();
        self.V = np.array(V).reshape((N,3)).copy();
        self.BT = np.array(BT).reshape((N,1)).copy();
        self.YBus = np.array(YBus).reshape((N,N)).copy();
        self.D = np.zeros((self.n,1));
        self.Max = MaxIter;
        self.Vlimit = Vlimit;
        self.Qlimit = Qlimit;
        self.Line = Line;
        self.__Sort();
        self.V[0:self.pq,0] = 1.0;

    def __Sort(self):
        self.indx = np.argsort(self.BT,axis=0).flatten();
        self.BT = self.BT[self.indx];
        self.P = self.P[self.indx];
        self.Q = self.Q[self.indx];
        self.V = self.V[self.indx];
        self.D = self.D[self.indx];
        self.pq = int(Counter(self.BT.flatten())['PQ']);

    def __P_calc(self,idx):
        Y = np.transpose(self.YBus[self.indx[idx]][self.indx]).reshape((self.n,1));
        return self.V[idx,0]*np.sum(self.V[:,0].reshape((self.n,1))*abs(Y)*np.cos(np.angle(Y)-self.D[idx,0]+self.D));

    def __Q_calc(self,idx):
        Y = np.transpose(self.YBus[self.indx[idx]][self.indx]).reshape((self.n,1));
        return -self.V[idx,0]*np.sum(self.V[:,0].reshape((self.n,1))*abs(Y)*np.sin(np.angle(Y)-self.D[idx,0]+self.D));

    def __Pij(self,idx,jdx):
        idx = int(idx);
        jdx = int(jdx);
        yi0 = self.Line[idx-1,3]*1j;
        yij = -self.YBus[idx-1][jdx-1];
        p1 = self.V[idx-1,0]*self.V[idx-1,0]*abs(yi0+yij)*np.cos(np.angle(yi0+yij));
        p2 = self.V[idx-1,0]*self.V[jdx-1,0]*abs(yij)*np.cos(np.angle(yij)-self.D[idx-1,0]+self.D[jdx-1,0]);
        return p1-p2;

    def __Qij(self,idx,jdx):
        idx = int(idx);
        jdx = int(jdx);
        yi0 = self.Line[idx-1,3]*1j;
        yij = -self.YBus[idx-1][jdx-1];
        p1 = self.V[idx-1,0]*self.V[idx-1,0]*abs(yi0+yij)*np.sin(np.angle(yi0+yij));
        p2 = self.V[idx-1,0]*self.V[jdx-1,0]*abs(yij)*np.sin(np.angle(yij)-self.D[idx-1,0]+self.D[jdx-1,0]);
        return -(p1-p2);

    def Solve(self):
        countVal = 0;
        for i in range(0,self.Max):
            countVal += 1;
            n = self.n;
            n_pq = self.pq;

            J = np.zeros((n_pq+n-1,n_pq+n-1));
            Err = np.zeros((n_pq+n-1,1));

            Err[:n-1,:] = np.array([[self.P[idx,0]-self.__P_calc(idx)] for idx in range(0,n-1)]).reshape((n-1,1));
            Err[n-1:,:] = np.array([[self.Q[idx,0]-self.__Q_calc(idx)] for idx in range(0,n_pq)]).reshape((n_pq,1));

            if (np.max(abs(Err)) < 1e-6):
                break;
            
            # J1 = P/V for (PQ+PV)x(PQ)
            if n_pq != 0:
                Y = self.YBus[self.indx[:-1],:][:,self.indx[:n_pq]];
                v = self.V[:-1,0].reshape((n-1,1));
                J[0:n-1,0:n_pq] = v*abs(Y)*np.cos(np.angle(Y)-self.D[:-1,:]+np.transpose(self.D[:n_pq,:]));
                Y = self.YBus[self.indx[:n_pq],:][:,self.indx];
                J[range(0,n_pq),range(0,n_pq)] += np.transpose(np.sum(np.transpose(self.V[:,0].reshape((self.n,1)))*abs(Y)
                    *np.cos(np.angle(Y)-self.D[:n_pq,:]+np.transpose(self.D)),axis=1));

            # J2 = Q/V for (PQ)x(PQ)
            if n_pq != 0:
                Y = self.YBus[self.indx[:n_pq],:][:,self.indx[:n_pq]];
                v = self.V[:n_pq,0].reshape((n_pq,1));
                J[n-1:,0:n_pq] = -v*abs(Y)*np.sin(np.angle(Y)-self.D[:n_pq,:]+np.transpose(self.D[:n_pq,:]));
                Y = self.YBus[self.indx[:n_pq],:][:,self.indx];
                J[n-1+np.array(range(0,n_pq)),range(0,n_pq)] -= np.transpose(np.sum(np.transpose(self.V[:,0].reshape((self.n,1)))*abs(Y)*
                    np.sin(np.angle(Y)-self.D[:n_pq,:]+np.transpose(self.D)),axis=1));

            # J3 = P/D for (PQ+PV)x(PQ+PV)
            Y = self.YBus[self.indx[:-1],:][:,self.indx[:-1]];
            v = self.V[:-1,0].reshape((n-1,1));
            J[0:n-1,n_pq:] = -v*np.transpose(v)*abs(Y)*np.sin(np.angle(Y)-self.D[:-1,:]+np.transpose(self.D[:-1,:]));
            Y = self.YBus[self.indx[:n-1],:][:,self.indx];
            J[range(0,n-1),n_pq+np.array(range(0,n-1))] += np.transpose(np.sum(v*np.transpose(self.V[:,0].reshape((self.n,1)))*abs(Y)*
                np.sin(np.angle(Y)-self.D[:n-1,:]+np.transpose(self.D)),axis=1));

            # J4 = Q/D for (PQ)x(PQ+PV)
            if n_pq != 0:
                Y = self.YBus[self.indx[:n_pq],:][:,self.indx[:-1]];
                v = self.V[:n_pq,0].reshape((n_pq,1));
                J[n-1:,n_pq:]=-v*np.transpose(self.V[:-1,0].reshape((n-1,1)))*abs(Y)*np.cos(np.angle(Y)-self.D[:n_pq,:]+np.transpose(self.D[:-1,:]));
                Y = self.YBus[self.indx[:n_pq],:][:,self.indx];
                J[n-1+np.array(range(0,n_pq)),n_pq+np.array(range(0,n_pq))] += np.transpose(np.sum(v*np.transpose(self.V[:,0].reshape((self.n,1)))
                    *abs(Y)*np.cos(np.angle(Y)-self.D[:n_pq,:]+np.transpose(self.D)),axis=1));

            if abs(np.linalg.det(J)) > 1e-3:
                delta = np.matmul(np.linalg.inv(J),Err);
                self.V[0:n_pq,0] += delta[0:n_pq].flatten();
                self.D[0:-1,0] += delta[n_pq:].flatten();
                self.Q[n_pq:-1,0] = [self.__Q_calc(idx) for idx in range(n_pq,n-1)];
                
                for i in range(0,self.n):
                    if self.Qlimit and self.Q[i][0]+self.Q[i][3] < self.Q[i][1] and abs(self.Q[i][1]-self.Q[i][2]) > 1e-10:
                        self.Q[i][0] = self.Q[i][1]-self.Q[i][3];
                        self.BT[i][0] = 'PQ';
                    elif self.Qlimit and self.Q[i][0]+self.Q[i][3] > self.Q[i][2] and abs(self.Q[i][1]-self.Q[i][2]) > 1e-10:
                        self.Q[i][0] = self.Q[i][2]-self.Q[i][3];
                        self.BT[i][0] = 'PQ';

                    if self.Vlimit and self.V[i][0] < self.V[i][1] and abs(self.V[i][1]-self.V[i][2]) > 1e-10:
                        self.V[i][0] = self.V[i][1];
                        self.BT[i][0] = 'PV';
                    elif self.Vlimit and self.V[i][0] > self.V[i][2] and abs(self.V[i][1]-self.V[i][2]) > 1e-10:
                        self.V[i][0] = self.V[i][2];
                        self.BT[i][0] = 'PV';
                
                tmpindx = list(self.indx);
                revindx = [tmpindx.index(i) for i in range(0,self.n)];
                self.BT = self.BT[revindx];
                self.P = self.P[revindx];
                self.Q = self.Q[revindx];
                self.V = self.V[revindx];
                self.D = self.D[revindx];
                self.__Sort();
                
        
        self.P[-1,0] = self.__P_calc(self.n-1);
        self.Q[-1,0] = self.__Q_calc(self.n-1);


        tmpindx = list(self.indx);
        revindx = [tmpindx.index(i) for i in range(0,self.n)];
        self.P = self.P[revindx];
        self.Q = self.Q[revindx];
        self.V = self.V[revindx];
        self.D = self.D[revindx];
        self.BT = self.BT[revindx];

        PL = [[self.__Pij(i,j),-self.__Pij(j,i)] for i,j in self.Line[:,(1,2)]];
        QL = [[self.__Qij(i,j),self.__Qij(j,i)] for i,j in self.Line[:,(1,2)]];
        Pavg = np.mean(PL,axis=1).flatten();
        Qavg = -np.diff(QL,axis=1).flatten();
        Ploss = abs(np.diff(PL,axis=1)).flatten();
        Qloss = np.sum(QL,axis=1).flatten();

        return [countVal,self.BT,self.P,self.Q,self.V,self.D,Pavg,Qavg,Ploss,Qloss];
