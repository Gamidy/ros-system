"""竞品数据批量导入"""
import sys
sys.path.insert(0, '/app/app')

from app.core.database import SessionLocal
from app.models.competitor import CompetitorModel

DATA = [
    # ═══ 欧盟/美国 ═══
    ("AUX","ASW-09A4","欧盟","分体式空调",2600,3000,"A++",28,52,"€599",2023),
    ("AUX","ASW-12A4","欧盟","分体式空调",3500,3800,"A++",30,54,"€699",2023),
    ("AUX","ASW-09A3","欧盟","分体式空调",2600,2900,"A+",30,53,"€499",2022),
    ("AUX","ASW-18A4","欧盟","分体式空调",5200,5600,"A++",32,56,"€899",2023),
    ("AUX","ASE-12M2A","美国","分体式空调",3517,3517,"SEER 15",45,55,"$499",2022),
    ("TCL","TAC-09CHSA","欧盟","分体式空调",2600,3000,"A++",28,52,"€549",2023),
    ("TCL","TAC-12CHSA","欧盟","分体式空调",3500,3800,"A++",30,54,"€649",2023),
    ("TCL","TAC-18CHSA","欧盟","分体式空调",5200,5600,"A++",32,56,"€849",2023),
    ("TCL","TAC-09CSD","美国","分体式空调",2637,2637,"SEER 14",42,50,"$399",2022),
    ("TCL","TAC-12CSD","美国","分体式空调",3517,3517,"SEER 14",45,52,"$449",2022),

    # ═══ 中东 ═══
    ("AUX","AUX-12K-SPLIT-SA","沙特阿拉伯","分体式空调",3516,3516,"1级",30,55,"SAR 800",2024),
    ("TCL","TAC-12CHSA-SA","沙特阿拉伯","分体式空调",3516,3516,"2级",32,56,"SAR 750",2023),
    ("AUX","AUX-18K-SPLIT-AE","阿联酋","分体式空调",5275,5275,"1级",35,58,"AED 1,100",2024),
    ("TCL","TAC-18CHSA-AE","阿联酋","分体式空调",5275,5275,"1级",34,57,"AED 1,050",2023),
    ("AUX","AUX-12K-SPLIT-KW","科威特","分体式空调",3516,3516,"1级",29,54,"KWD 95",2024),
    ("TCL","TAC-12CHSA-KW","科威特","分体式空调",3516,None,"2级",31,56,"KWD 88",2023),
    ("AUX","AUX-24K-SPLIT-IR","伊朗","分体式空调",7033,7033,"1级",38,60,"IRR 1,300",2024),
    ("TCL","TAC-24CHSA-IR","伊朗","分体式空调",7033,None,"3级",40,62,"IRR 1,200",2023),
    ("AUX","AUX-12K-SPLIT-IL","以色列","分体式空调",3516,3516,"A++",27,52,"ILS 1,100",2024),
    ("TCL","TAC-12WKA","以色列","分体式空调",3516,3516,"A+",29,54,"ILS 1,000",2023),

    # ═══ 南美 ═══
    ("TCL","TAC-09CHSA/BR","巴西","分体式空调",2637,None,"A",28,50,"BRL 1,899",2024),
    ("TCL","TAC-12CHSA/AR","阿根廷","分体式空调",3516,None,"A",30,52,"ARS 450,000",2024),
    ("TCL","TAC-18HSA/CL","智利","分体式空调",5275,5275,"A",34,56,"CLP 499,990",2023),
    ("TCL","TAC-09CHSA/CO","哥伦比亚","分体式空调",2637,None,"A",28,50,"COP 1,890,000",2024),
    ("TCL","TAC-12CHSA/MX","墨西哥","分体式空调",3516,None,"A",30,52,"MXN 6,499",2024),

    # ═══ 非洲 ═══
    ("TCL","TAC-12CHSA-ZA","南非","分体式空调",3516,3516,"A++",32,52,"ZAR 4,999",2023),
    ("TCL","TAC-18CHSA-ZA","南非","分体式空调",5275,5275,"A+",35,55,"ZAR 6,799",2023),
    ("TCL","TAC-24CHSA-EG","埃及","分体式空调",7033,6150,"A++",38,58,"EGP 15,200",2023),
    ("TCL","TAC-09CHSA-NG","尼日利亚","分体式空调",2637,None,"A",28,48,"NGN 289,000",2023),
    ("TCL","TAC-12CHSA-GH","加纳","分体式空调",3516,None,None,32,52,"GHS 6,200",2024),

    # ═══ 俄罗斯/乌克兰/台湾 ═══
    ("AUX","KFR-35GW/A","俄罗斯","分体式空调",3516,3663,"A",30,50,"RUB 29,500",2023),
    ("AUX","KFR-50LW/B","俄罗斯","分体式空调",5275,5568,"A+",35,55,"RUB 48,000",2024),
    ("TCL","TAC-12CHSA-RU","俄罗斯","分体式空调",3516,3516,"A+",32,52,"RUB 34,900",2023),
    ("TCL","TAC-12CHSA-UA","乌克兰","分体式空调",3516,3663,"A",32,52,"UAH 14,990",2023),
    ("TCL","TAC-36W/GA","台湾","分体式空调",10550,11722,"CSPF 1級",32,55,"NT$ 28,900",2024),
    ("AUX","GA35定頻","台湾","分体式空调",3516,None,"CSPF 5級",34,52,"NT$ 14,500",2023),

    # ═══ 东南亚 ═══
    ("AUX","KFR-35GW/BpR3","越南","分体式空调",3516,3809,"CSPF 4.7",28,52,"VND 8,500,000",2023),
    ("AUX","KFR-50GW/BpR3","越南","分体式空调",5275,5568,"CSPF 4.5",32,55,"VND 11,500,000",2023),
    ("TCL","TAC-12CSF","越南","分体式空调",3516,3809,"CSPF 4.2",30,53,"VND 7,800,000",2023),
    ("TCL","TAC-18INV","越南","分体式空调",5275,5275,"CSPF 4.0",33,56,"VND 10,900,000",2023),
    ("AUX","ASW-09ID","印度尼西亚","分体式空调",2637,2637,"A++",28,50,"IDR 3,500,000",2024),
    ("TCL","TAC-09INV-ID","印度尼西亚","分体式空调",2637,2784,"A+",27,52,"IDR 3,200,000",2023),
    ("AUX","ASW-12MY","马来西亚","分体式空调",3516,3809,"A++",29,53,"MYR 2,500",2024),
    ("TCL","TAC-12INV-MY","马来西亚","分体式空调",3516,3663,"A+",30,54,"MYR 2,200",2023),
    ("TCL","TAC-18INV-PK","巴基斯坦","分体式空调",5275,5275,"A+",32,55,"PKR 85,000",2023),
    ("AUX","ASW-18PK","巴基斯坦","分体式空调",5275,5568,"A++",31,54,"PKR 95,000",2024),
]

def main():
    db = SessionLocal()
    try:
        # 清空已有竞品数据（重新导入）
        existing = db.query(CompetitorModel).count()
        print(f"已有 {existing} 条记录")

        count = 0
        for row in DATA:
            brand, model, market, ptype, cool_w, heat_w, energy, ndb, odb, price, year = row
            item = CompetitorModel(
                brand=brand, model=model, market=market, product_type=ptype,
                cooling_capacity_w=cool_w, heating_capacity_w=heat_w,
                energy_rating=energy,
                noise_indoor_db=float(ndb) if ndb else None,
                noise_outdoor_db=float(odb) if odb else None,
                factory_price=price, launch_year=year,
                notes="AI采集",
            )
            db.add(item)
            count += 1

        db.commit()
        total = db.query(CompetitorModel).count()
        print(f"导入完成: 新增 {count} 条，总计 {total} 条")
    finally:
        db.close()

if __name__ == "__main__":
    main()
