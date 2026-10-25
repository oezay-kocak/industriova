"""Counterfactual audit only. No runtime source modifications."""
from dataclasses import dataclass
from math import ceil

BOARDS={'factory':(5,10,3),'resources':(3,10,1),'energy':(3,5,1)}
START={'garage_depot':3,'rail_station':2,'airport':2,'harbor':2}


@dataclass(frozen=True)
class Curve:
    name:str
    slot_bases:tuple
    freight_slot:float
    freight_line:float
    freight_build:tuple

    def slot(self,board,line,number):
        start=BOARDS[board][2]
        if self.name=='old':return 120+(number-start-1)*90+(line-1)*35
        return self.slot_bases[('factory','resources','energy').index(board)]*(number-start)

    def line(self,board,number):
        if self.name=='old':return 750+max(0,number-3)*500
        _,cap,start=BOARDS[board]
        base=ceil((self.slot(board,1,cap)*start+1)/100)*100
        return base*(number-1)**2

    def full(self,board):
        lines,cap,start=BOARDS[board];initial=2 if board=='factory' and self.name=='old' else 1
        return sum(self.line(board,line) if line>initial else 0 for line in range(1,lines+1))+sum(self.slot(board,line,k) for line in range(1,lines+1) for k in range(start+1,cap+1))

    def build(self,board,count):
        if self.name=='old':return 1000*(1+max(0,count-1))**2.5
        if count==0:return 500 if board=='resources' else 1000
        lines,cap,start=BOARDS[board]
        extras=sum(self.slot(board,1,k) for k in range(start+1,cap+1))
        last=self.line(board,lines)+extras
        second=ceil((1.05*last-extras)/100)*100
        return ceil(second*count**2.5/100)*100

    def freight_expansion(self,kind,index):
        if self.name=='old':return 300*(1+index-START[kind])**2
        line,pos=divmod(index,8)
        if line and pos==0:return self.freight_line*line**2
        start=START[kind] if line==0 else 1
        return self.freight_slot*(pos+1-start)

    def freight_facility(self,kind,count):
        values=dict(zip(('garage_depot','rail_station','airport','harbor'),self.freight_build))
        return values[kind]*(1+count)**2


CURVES=(Curve('old',(0,0,0),0,0,(500,1500,3500,2500)),
        Curve('A',(40,90,100),60,900,(2000,8000,30000,100000)),
        Curve('B',(60,100,120),90,1800,(3000,15000,60000,180000)),
        Curve('C',(90,120,160),120,2400,(5000,30000,90000,250000)))


def production_layout(curve,board,required):
    """Minimum cash to own >=required slots, all line choices remain possible."""
    maximum,cap,start=BOARDS[board];initial=2 if board=='factory' and curve.name=='old' else 1
    dp={0:(0,[])}
    for line in range(1,maximum+1):
        choices=[(0,0)] if line>initial else []
        choices += [(n,(curve.line(board,line) if line>initial else 0)+sum(curve.slot(board,line,k) for k in range(start+1,n+1))) for n in range(start,cap+1)]
        next_dp={}
        for previous,(price,layout) in dp.items():
            for n,extra in choices:
                key=previous+n;candidate=(price+extra,layout+[n])
                if key not in next_dp or candidate[0]<next_dp[key][0]:next_dp[key]=candidate
        dp=next_dp
    return min((v for n,v in dp.items() if n>=required),key=lambda x:x[0])


def checks(curve):
    result={}
    for board,(lines,cap,start) in BOARDS.items():
        extras=sum(curve.slot(board,1,k) for k in range(start+1,cap+1))
        result[board]=dict(first_line_expansion=extras,full_expansion=curve.full(board),second_facility=curve.build(board,1),
            last_slot=curve.slot(board,1,cap),second_line=curve.line(board,2),
            later_line_not_cheaper_per_start_slot=curve.line(board,2)/start>curve.slot(board,1,cap),
            new_full_first_line_not_cheaper_than_last_line=curve.build(board,1)+extras>=curve.line(board,lines)+extras)
    second_line=sum(curve.freight_expansion('garage_depot',i) for i in range(8,16))+8*205
    second_garage=curve.freight_facility('garage_depot',1)+sum(curve.freight_expansion('garage_depot',i) for i in range(3,8))+8*205
    result['garage']=dict(second_fleet_full_with_vehicles=second_line,second_garage_full_with_vehicles=second_garage,prefer_second_fleet=second_line<second_garage)
    return result
