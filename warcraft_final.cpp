#include<iostream>
#include<string>
#include<cstring>
#include<cstdlib>
#include<cstdio>
#include<algorithm>
#include<queue>
#include<deque>
using namespace std;

int gametime = 0;
bool gameover = 0;

class warrior;//声明warrior类
class troop;//声明troop类
class redtroop;
class bluetroop;

class weapon
{
protected:
public:
    char name[10];
    int attack_ability;
    int totalnum;
    weapon() {}
    weapon(const char *Name, int ATK) : attack_ability(ATK),totalnum(0)
    {
        strcpy(name, Name);
    }
    weapon(const weapon &weapon1)
    {
        strcpy(name, weapon1.name);
        attack_ability = weapon1.attack_ability;
    }
    virtual ~weapon(){}
};
class sword : public weapon
{
public:
    sword():weapon("sword",0){}
    sword(int atk) : weapon("sword", atk){}
    sword(const sword &sword1) : weapon(sword1.name, sword1.attack_ability) {}
    virtual ~sword(){}
};
class bomb : public weapon
{
public:
    bomb() : weapon("bomb", 0){}
    bomb(int atk) : weapon("bomb", atk) {}
    bomb(const bomb &bomb1) : weapon(bomb1.name, bomb1.attack_ability){}
    virtual ~bomb(){}
};
class arrow : public weapon
{
public:
    static int arrow_atk;
    int usedZeroNum;
    int usedOnceNum;
    int used_time;
    arrow():weapon("arrow",0),used_time(0),usedOnceNum(0),usedZeroNum(0){}
    arrow(int atk) : weapon("sword", atk), used_time(0), usedOnceNum(0), usedZeroNum(0) {}
    arrow(const arrow &arrow1) : weapon(arrow1.name, arrow1.attack_ability){}
    virtual ~arrow() {}
};
int arrow::arrow_atk = 0;

class warrior{
    protected:
    public:
        char name[10];
        int blood;
        int attack_ability;
        int ID;
        sword swords;
        bomb bombs;
        arrow arrows;
        int totalWeaponNum;
        bool sneakKilled;
        warrior(const char* Name):totalWeaponNum(0),sneakKilled(0){
            strcpy(name, Name);
        }
        virtual ~warrior(){}
};

class dragon:public warrior{
    public:
        float morale;
        dragon(char troopColor, int id);
        dragon():warrior("dragon"){}
        ~dragon(){}
};
class ninja:public warrior{
    public:
        ninja(char troopColor, int id);
        ninja() : warrior("ninja") {}
        ~ninja(){}
};
class iceman:public warrior{
    public:
        int marchSteps;
        iceman(char troopColor, int id);
        iceman() :warrior("iceman") {}
        ~iceman(){}
};
class lion:public warrior{
    public:
        int loyalty;
        int blood_copy;
        static int fear;//lion前进一步减少的生命值
        lion(char troopColor, int id);
        lion() : warrior("lion") {}
        ~lion() {}
};
int lion::fear = 0;
class wolf:public warrior{
    public:
        wolf(char troopColor, int id);
        wolf():warrior("wolf"){}
        ~wolf(){}
};

class troop{
    public:
        int IDofNowMakingWarrior;
        int loopptr;
        bool stopmaking;
        warrior *sequence[5];
};
class redtroop:public troop{
    public:
        static int blood;
        static int dragon_attr[2];
        static int iceman_attr[2];
        static int ninja_attr[2];
        static int lion_attr[2];
        static int wolf_attr[2];
        static int win;
        iceman icm;
        dragon drg;
        ninja nij;
        lion lin;
        wolf wlf;
        redtroop(){
            icm.blood = iceman_attr[0];
            icm.attack_ability = iceman_attr[1];
            drg.blood = dragon_attr[0];
            drg.attack_ability = dragon_attr[1];
            nij.blood = ninja_attr[0];
            nij.attack_ability = ninja_attr[1];
            lin.blood = lion_attr[0];
            lin.attack_ability = lion_attr[1];
            wlf.blood = wolf_attr[0];
            wlf.attack_ability = wolf_attr[1];
            IDofNowMakingWarrior = 0;
            loopptr = 0;
            stopmaking = 0;
            win = 0;
            sequence[0] = &icm;
            sequence[1] = &lin;
            sequence[2] = &wlf;
            sequence[3] = &nij;
            sequence[4] = &drg;
        }
};
int redtroop::win = 0;
int redtroop:: blood = 0;
int redtroop::dragon_attr[2] = {0, 0};
int redtroop::iceman_attr[2] = {0, 0};
int redtroop::ninja_attr[2] = {0, 0};
int redtroop::lion_attr[2] = {0, 0};
int redtroop::wolf_attr[2] = {0, 0};

class bluetroop:public troop{
    public:
        static int blood;
        static int dragon_attr[2];
        static int iceman_attr[2];
        static int ninja_attr[2];
        static int lion_attr[2];
        static int wolf_attr[2];
        static int win;
        iceman icm;
        dragon drg;
        ninja nij;
        lion lin;
        wolf wlf;
        bluetroop()
        {
            icm.blood = iceman_attr[0];
            icm.attack_ability = iceman_attr[1];
            drg.blood = dragon_attr[0];
            drg.attack_ability = dragon_attr[1];
            nij.blood = ninja_attr[0];
            nij.attack_ability = ninja_attr[1];
            lin.blood = lion_attr[0];
            lin.attack_ability = lion_attr[1];
            wlf.blood = wolf_attr[0];
            wlf.attack_ability = wolf_attr[1];
            IDofNowMakingWarrior = 0;
            loopptr = 0;
            stopmaking = 0;
            win = 0;
            sequence[0] = &lin;
            sequence[1] = &drg;
            sequence[2] = &nij;
            sequence[3] = &icm;
            sequence[4] = &wlf;
        }
};
int bluetroop::win = 0;
int bluetroop::blood = 0;
int bluetroop::dragon_attr[2] = {0, 0};
int bluetroop::iceman_attr[2] = {0, 0};
int bluetroop::ninja_attr[2] = {0, 0};
int bluetroop::lion_attr[2] = {0, 0};
int bluetroop::wolf_attr[2] = {0, 0};

dragon::dragon(char troopColor, int id) : warrior("dragon")
{
        switch (troopColor)
        {
        case 'r':
            blood = redtroop::dragon_attr[0];
            attack_ability = redtroop::dragon_attr[1];
            break;
        case 'b':
            blood = bluetroop::dragon_attr[0];
            attack_ability = bluetroop::dragon_attr[1];
            break;
        }
        ID = id;
        switch (ID % 3)
        {
        case 0:
            swords.totalnum += 1;
            totalWeaponNum += 1;
            swords.attack_ability = attack_ability * 2 / 10;
            if (swords.attack_ability == 0)
            {
                swords.totalnum -= 1;
                totalWeaponNum -= 1;
            }
            break;
        case 1:
            bombs.totalnum += 1;
            totalWeaponNum += 1;
            break;
        case 2:
            arrows.totalnum += 1;
            totalWeaponNum += 1;
            break;
        }
}
ninja::ninja(char troopColor, int id) : warrior("ninja")
{
        switch (troopColor)
        {
        case 'r':
            blood = redtroop::ninja_attr[0];
            attack_ability = redtroop::ninja_attr[1];
            break;
        case 'b':
            blood = bluetroop::ninja_attr[0];
            attack_ability = bluetroop::ninja_attr[1];
            break;
        }
        ID = id;
        switch (ID % 3)
        {
        case 0:
            swords.totalnum += 1;
            bombs.totalnum += 1;
            totalWeaponNum += 2;
            swords.attack_ability = attack_ability * 2 / 10;
            if (swords.attack_ability == 0)
            {
                swords.totalnum -= 1;
                totalWeaponNum -= 1;
            }
            break;
        case 1:
            bombs.totalnum += 1;
            arrows.totalnum += 1;
            arrows.usedZeroNum += 1;
            totalWeaponNum += 2;
            break;
        case 2:
            swords.totalnum += 1;
            arrows.totalnum += 1;
            arrows.usedZeroNum += 1;
            totalWeaponNum += 2;
            swords.attack_ability = attack_ability * 2 / 10;
            if (swords.attack_ability == 0)
            {
                swords.totalnum -= 1;
                totalWeaponNum -= 1;
            }
            break;
        }
}
iceman::iceman(char troopColor, int id) : warrior("iceman"),marchSteps(0)
{
        switch (troopColor)
        {
        case 'r':
            blood = redtroop::iceman_attr[0];
            attack_ability = redtroop::iceman_attr[1];
            break;
        case 'b':
            blood = bluetroop::iceman_attr[0];
            attack_ability = bluetroop::iceman_attr[1];
            break;
        }
        ID = id;
        switch (ID % 3)
        {
        case 0:
            swords.totalnum += 1;
            totalWeaponNum += 1;
            swords.attack_ability = attack_ability * 2 / 10;
            if(swords.attack_ability==0){
                swords.totalnum -= 1;
                totalWeaponNum -= 1;
            }
            break;
        case 1:
            bombs.totalnum += 1;
            totalWeaponNum += 1;
            break;
        case 2:
            arrows.totalnum += 1;
            totalWeaponNum += 1;
            break;
        }
}
lion::lion(char troopColor, int id) : warrior("lion"),blood_copy(0)
{
        switch (troopColor)
        {
        case 'r':
            blood = redtroop::lion_attr[0];
            attack_ability = redtroop::lion_attr[1];
            loyalty = redtroop::blood;
            break;
        case 'b':
            blood = bluetroop::lion_attr[0];
            attack_ability = bluetroop::lion_attr[1];
            loyalty = bluetroop::blood;
            break;
        }
        ID = id;
}
wolf::wolf(char troopColor, int id) : warrior("wolf")
{
        switch (troopColor)
        {
        case 'r':
            blood = redtroop::wolf_attr[0];
            attack_ability = redtroop::wolf_attr[1];
            break;
        case 'b':
            blood = bluetroop::wolf_attr[0];
            attack_ability = bluetroop::wolf_attr[1];
            break;
        }
        ID = id;
}

class castle{
public:
    int ID;
    int blood;
    char flag;
    char nowBetter;
    castle *preCastle;
    castle *nextCastle;
    warrior *redWarrior;
    warrior *redWarrior_tmp;
    warrior *blueWarrior;
    warrior *blueWarrior_tmp;
    castle():redWarrior(nullptr),blueWarrior(nullptr),redWarrior_tmp(nullptr),blueWarrior_tmp(nullptr),preCastle(nullptr),nextCastle(nullptr){
            blood = 0;
            flag = 'n';
            nowBetter = 'n';
    }
    ~castle(){}
    void fight(){
        if (redWarrior==nullptr||blueWarrior==nullptr)
            return;
        if(redWarrior->blood<=0||blueWarrior->blood<=0)
            return;
        if(flag=='r'||(flag=='n'&&ID%2==1)){
            std::printf("%03d:%02d red %s %d attacked blue %s %d in city %d with %d elements and force %d\n",gametime/60,gametime%60,
            redWarrior->name,redWarrior->ID,blueWarrior->name,blueWarrior->ID,ID,redWarrior->blood,redWarrior->attack_ability);
            if(redWarrior->swords.totalnum>0){
                blueWarrior->blood -= (redWarrior->attack_ability + redWarrior->swords.attack_ability);
                redWarrior->swords.attack_ability = redWarrior->swords.attack_ability * 8 / 10;
                if(redWarrior->swords.attack_ability==0)
                    redWarrior->swords.totalnum = 0;
            }
            else
                blueWarrior->blood -= (redWarrior->attack_ability );
            if(blueWarrior->blood>0&&strcmp(blueWarrior->name,"ninja")!=0){
                std::printf("%03d:%02d blue %s %d fought back against red %s %d in city %d\n", gametime / 60, gametime % 60,
                       blueWarrior->name, blueWarrior->ID, redWarrior->name, redWarrior->ID, ID);
                if(blueWarrior->swords.totalnum>0){
                    redWarrior->blood -= (blueWarrior->attack_ability / 2 + blueWarrior->swords.attack_ability);
                    blueWarrior->swords.attack_ability = blueWarrior->swords.attack_ability * 8 / 10;
                    if(blueWarrior->swords.attack_ability==0)
                        blueWarrior->swords.totalnum = 0;
                }
                else
                    redWarrior->blood -= (blueWarrior->attack_ability / 2 );
            }
        }
        else{
            std::printf("%03d:%02d blue %s %d attacked red %s %d in city %d with %d elements and force %d\n", gametime / 60, gametime % 60,
                    blueWarrior->name, blueWarrior->ID, redWarrior->name, redWarrior->ID, ID, blueWarrior->blood, blueWarrior->attack_ability);
            if (blueWarrior->swords.totalnum > 0)
            {
                redWarrior->blood -= (blueWarrior->attack_ability + blueWarrior->swords.attack_ability);
                blueWarrior->swords.attack_ability = blueWarrior->swords.attack_ability * 8 / 10;
                if (blueWarrior->swords.attack_ability == 0)
                    blueWarrior->swords.totalnum = 0;
            }
            else
                redWarrior->blood -= (blueWarrior->attack_ability);
            if(redWarrior->blood>0&&strcmp(redWarrior->name,"ninja")!=0){
                std::printf("%03d:%02d red %s %d fought back against blue %s %d in city %d\n", gametime / 60, gametime % 60,
                       redWarrior->name, redWarrior->ID, blueWarrior->name, blueWarrior->ID, ID);
                if (redWarrior->swords.totalnum > 0)
                {
                    blueWarrior->blood -= (redWarrior->attack_ability/2 + redWarrior->swords.attack_ability);
                    redWarrior->swords.attack_ability = redWarrior->swords.attack_ability * 8 / 10;
                    if (redWarrior->swords.attack_ability == 0)
                        redWarrior->swords.totalnum = 0;
                }
                else
                    blueWarrior->blood -= (redWarrior->attack_ability/2);
            }
        }
    }
    void printOutcome(){
        if(redWarrior->blood<=0){
            if(blueWarrior->blood<=0){
                delete blueWarrior;
                blueWarrior = nullptr;
                delete redWarrior;
                redWarrior = nullptr;
                return;
            }
            if(!redWarrior->sneakKilled)
                std::printf("%03d:%02d red %s %d was killed in city %d\n", gametime / 60, gametime % 60,
                        redWarrior->name, redWarrior->ID, ID);
            if(strcmp(blueWarrior->name,"dragon")==0){
                dragon *pdragon = (dragon*)blueWarrior;
                pdragon->morale += 0.2;
                if(pdragon->morale>0.8&&(flag=='b'||(flag=='n'&&ID%2==0)))
                    std::printf("%03d:%02d blue dragon %d yelled in city %d\n", gametime / 60, gametime % 60, blueWarrior->ID, ID);
            }
            if(strcmp(blueWarrior->name,"wolf")==0){
                if(blueWarrior->swords.totalnum==0&&redWarrior->swords.totalnum>0){
                    blueWarrior->swords.totalnum += 1;
                    blueWarrior->swords.attack_ability = redWarrior->swords.attack_ability;
                }
                if(blueWarrior->bombs.totalnum==0&&redWarrior->bombs.totalnum>0){
                    blueWarrior->bombs.totalnum += 1;
                }
                if(blueWarrior->arrows.totalnum==0&&redWarrior->arrows.totalnum>0){
                    blueWarrior->arrows.totalnum += 1;
                    blueWarrior->arrows.used_time = redWarrior->arrows.used_time;
                }
            }
            std::printf("%03d:%02d blue %s %d earned %d elements for his headquarter\n", gametime / 60, gametime % 60,
                   blueWarrior->name, blueWarrior->ID, blood);
            if(strcmp(redWarrior->name,"lion")==0){
                lion *plion = (lion *)redWarrior;
                blueWarrior->blood += plion->blood_copy;
            }
            if(nowBetter=='b'){
                nowBetter = 'n';
                if(flag!='b'){
                    flag = 'b';
                    std::printf("%03d:%02d blue flag raised in city %d\n", gametime / 60, gametime % 60, ID);
                }
            }
            else
                nowBetter = 'b';
        }
        else{
            if(blueWarrior->blood<=0){
                if(!blueWarrior->sneakKilled)
                    std::printf("%03d:%02d blue %s %d was killed in city %d\n", gametime / 60, gametime % 60,
                            blueWarrior->name, blueWarrior->ID, ID);
                if (strcmp(redWarrior->name, "dragon") == 0)
                {
                    dragon *pdragon = (dragon*)redWarrior;
                    pdragon->morale += 0.2;
                    if (pdragon->morale > 0.8 && (flag == 'r' || (flag == 'n' && ID % 2 == 1)))
                        std::printf("%03d:%02d red dragon %d yelled in city %d\n", gametime / 60, gametime % 60, redWarrior->ID, ID);
                }
                if (strcmp(redWarrior->name, "wolf") == 0)
                {
                    if (redWarrior->swords.totalnum == 0 && blueWarrior->swords.totalnum > 0)
                    {
                        redWarrior->swords.totalnum += 1;
                        redWarrior->swords.attack_ability = blueWarrior->swords.attack_ability;
                    }
                    if (redWarrior->bombs.totalnum == 0 && blueWarrior->bombs.totalnum > 0)
                    {
                        redWarrior->bombs.totalnum += 1;
                    }
                    if (redWarrior->arrows.totalnum == 0 && blueWarrior->arrows.totalnum > 0)
                    {
                        redWarrior->arrows.totalnum += 1;
                        redWarrior->arrows.used_time = blueWarrior->arrows.used_time;
                    }
                }
                std::printf("%03d:%02d red %s %d earned %d elements for his headquarter\n", gametime / 60, gametime % 60,
                       redWarrior->name, redWarrior->ID, blood);
                if (strcmp(blueWarrior->name, "lion") == 0)
                {
                    lion *plion = (lion *)blueWarrior;
                    redWarrior->blood += plion->blood_copy;
                }
                if (nowBetter == 'r')
                {
                    nowBetter = 'n';
                    if (flag != 'r')
                    {
                        flag = 'r';
                        std::printf("%03d:%02d red flag raised in city %d\n", gametime / 60, gametime % 60, ID);
                    }
                }
                else
                    nowBetter = 'r';

            }
            else{
                nowBetter = 'n';
                if (strcmp(redWarrior->name, "dragon") == 0)
                {
                    dragon *pdragon = (dragon *)redWarrior;
                    pdragon->morale -= 0.2;
                    if (pdragon->morale > 0.8 && (flag == 'r' || (flag == 'n' && ID % 2 == 1)))
                        std::printf("%03d:%02d red dragon %d yelled in city %d\n", gametime / 60, gametime % 60, redWarrior->ID, ID);
                }
                else if(strcmp(redWarrior->name,"lion")==0){
                    lion *plion = (lion *)redWarrior;
                    plion->loyalty -= plion->fear;
                }
                if (strcmp(blueWarrior->name, "dragon") == 0)
                {
                    dragon *pdragon = (dragon *)blueWarrior;
                    pdragon->morale -= 0.2;
                    if (pdragon->morale > 0.8 && (flag == 'b' || (flag == 'n' && ID % 2 == 0)))
                        std::printf("%03d:%02d blue dragon %d yelled in city %d\n", gametime / 60, gametime % 60, blueWarrior->ID, ID);
                }
                else if (strcmp(blueWarrior->name, "lion") == 0)
                {
                    lion *plion = (lion *)blueWarrior;
                    plion->loyalty -= plion->fear;
                }
            }
        }
    }
};
void redmarch(castle* nowCastle,int citys){
    if(nowCastle->preCastle!=nullptr){//不是红司令部
        if(nowCastle->ID!=citys+1){//不是蓝司令部
            nowCastle->redWarrior_tmp = nowCastle->redWarrior;
            nowCastle->redWarrior = nowCastle->preCastle->redWarrior_tmp;
            nowCastle->preCastle->redWarrior_tmp = nullptr;
        }
        else{
            if (nowCastle->redWarrior_tmp == nullptr){
                nowCastle->redWarrior_tmp = nowCastle->redWarrior;
                nowCastle->redWarrior = nowCastle->preCastle->redWarrior_tmp;
                nowCastle->preCastle->redWarrior_tmp = nullptr;
            }
            else{
                nowCastle->redWarrior = nowCastle->preCastle->redWarrior_tmp;
                nowCastle->preCastle->redWarrior_tmp = nullptr;
            }
        }
        if(nowCastle->redWarrior==nullptr)
            return;
        if(strcmp(nowCastle->redWarrior->name,"iceman")==0){
            iceman *piceman = (iceman*)nowCastle->redWarrior;
            if(piceman->marchSteps==1){
                piceman->marchSteps = 0;
                piceman->blood = max(1, piceman->blood - 9);
                piceman->attack_ability += 20;
            }
            else
                piceman->marchSteps += 1;
        }
        if(nowCastle->ID==citys+1){
            std::printf("%03d:%02d red %s %d reached blue headquarter with %d elements and force %d\n", gametime / 60, gametime % 60, 
            nowCastle->redWarrior->name, nowCastle->redWarrior->ID, nowCastle->redWarrior->blood, nowCastle->redWarrior->attack_ability);
            redtroop::win += 1;
            if(redtroop::win==2){
                std::printf("%03d:%02d blue headquarter was taken\n", gametime / 60, gametime % 60);
            }
        }
        else
            std::printf("%03d:%02d red %s %d marched to city %d with %d elements and force %d\n", gametime / 60, gametime % 60, 
            nowCastle->redWarrior->name, nowCastle->redWarrior->ID, nowCastle->ID, nowCastle->redWarrior->blood, nowCastle->redWarrior->attack_ability);
    }
    
}
void bluemarch(castle* nowCastle,int citys){
    if(nowCastle->nextCastle!=nullptr){
        if(nowCastle->preCastle!=nullptr){
            nowCastle->blueWarrior = nowCastle->nextCastle->blueWarrior;
            nowCastle->nextCastle->blueWarrior = nullptr;
        }
        else{
            if(nowCastle->blueWarrior_tmp==nullptr){
                nowCastle->blueWarrior_tmp = nowCastle->blueWarrior;
            }
            nowCastle->blueWarrior = nowCastle->nextCastle->blueWarrior;
            nowCastle->nextCastle->blueWarrior = nullptr;
        }
        if (nowCastle->blueWarrior == nullptr)
            return;
        if (strcmp(nowCastle->blueWarrior->name, "iceman") == 0)
        {
            iceman *piceman = (iceman *)nowCastle->blueWarrior;
            if (piceman->marchSteps == 1)
            {
                piceman->marchSteps = 0;
                piceman->blood = max(1, piceman->blood - 9);
                piceman->attack_ability += 20;
            }
            else
                piceman->marchSteps += 1;
        }
        if (nowCastle->ID == 0)
        {
            std::printf("%03d:%02d blue %s %d reached red headquarter with %d elements and force %d\n", gametime / 60, gametime % 60,
                    nowCastle->blueWarrior->name, nowCastle->blueWarrior->ID, nowCastle->blueWarrior->blood, nowCastle->blueWarrior->attack_ability);
            bluetroop::win += 1;
            if(bluetroop::win==2){
                std::printf("%03d:%02d red headquarter was taken\n", gametime / 60, gametime % 60);
            }
        }
        else
            std::printf("%03d:%02d blue %s %d marched to city %d with %d elements and force %d\n", gametime / 60,
                    gametime % 60, nowCastle->blueWarrior->name, nowCastle->blueWarrior->ID, nowCastle->ID, nowCastle->blueWarrior->blood, nowCastle->blueWarrior->attack_ability);
    }
}
void sneakArrowAttack(castle* nowCastle,int citys){
    castle *pCastle = nowCastle;
    for (int i = 0; i <= citys+1;++i){
        if(i<citys){
            if(nowCastle->redWarrior&&nowCastle->nextCastle->blueWarrior&&nowCastle->redWarrior->arrows.totalnum>0){
                nowCastle->nextCastle->blueWarrior->blood -= arrow::arrow_atk;
                if(nowCastle->nextCastle->blueWarrior->blood>0)
                    std::printf("%03d:%02d red %s %d shot\n",gametime/60,gametime%60,
                    nowCastle->redWarrior->name,nowCastle->redWarrior->ID);
                else
                {
                    nowCastle->nextCastle->blueWarrior->sneakKilled = 1;
                    std::printf("%03d:%02d red %s %d shot and killed blue %s %d\n",
                           gametime / 60, gametime % 60, nowCastle->redWarrior->name, nowCastle->redWarrior->ID,
                           nowCastle->nextCastle->blueWarrior->name, nowCastle->nextCastle->blueWarrior->ID);
                }
                if (++(nowCastle->redWarrior->arrows.used_time) == 3)
                {
                    nowCastle->redWarrior->arrows.totalnum = 0;
                    nowCastle->redWarrior->arrows.used_time = 0;
                }
            }
        }
        if(i>1){
            if(nowCastle->blueWarrior&&nowCastle->preCastle->redWarrior&&nowCastle->blueWarrior->arrows.totalnum>0){
                nowCastle->preCastle->redWarrior->blood -= arrow::arrow_atk;
                if (nowCastle->preCastle->redWarrior->blood > 0)
                    std::printf("%03d:%02d blue %s %d shot\n", gametime / 60, gametime % 60,
                           nowCastle->blueWarrior->name, nowCastle->blueWarrior->ID);
                else
                {
                    nowCastle->preCastle->redWarrior->sneakKilled = 1;
                    std::printf("%03d:%02d blue %s %d shot and killed red %s %d\n",
                           gametime / 60, gametime % 60, nowCastle->blueWarrior->name, nowCastle->blueWarrior->ID,
                           nowCastle->preCastle->redWarrior->name, nowCastle->preCastle->redWarrior->ID);
                }
                if (++(nowCastle->blueWarrior->arrows.used_time) == 3)
                {
                    nowCastle->blueWarrior->arrows.totalnum = 0;
                    nowCastle->blueWarrior->arrows.used_time = 0;
                }
            }
        }
        ++nowCastle;
    }
    for (int i = 1; i <= citys;++i){
        ++pCastle;
        if(pCastle->redWarrior&&!pCastle->blueWarrior){
            if(pCastle->redWarrior->blood<=0){
                delete pCastle->redWarrior;
                pCastle->redWarrior = nullptr;
            }
        }
        else if(pCastle->blueWarrior&&!pCastle->redWarrior){
            if(pCastle->blueWarrior->blood<=0){
                delete pCastle->blueWarrior;
                pCastle->blueWarrior = nullptr;
            }
        }
    }
}
void perishBombAttack(castle* nowCastle,int citys){
    for (int i = 1; i <= citys;++i){
        nowCastle++;
        if(nowCastle->redWarrior&&nowCastle->blueWarrior&&nowCastle->redWarrior->blood>0&&nowCastle->blueWarrior->blood>0){
            if(nowCastle->flag=='r'||(nowCastle->flag=='n'&&i%2==1)){
                bool judge1 = (strcmp(nowCastle->blueWarrior->name, "ninja") == 0);
                bool judge2 = 0;
                if(nowCastle->redWarrior->swords.totalnum>0){
                    judge2 = nowCastle->redWarrior->swords.attack_ability + nowCastle->redWarrior->attack_ability >= nowCastle->blueWarrior->blood;
                }
                else{
                    judge2 = nowCastle->redWarrior->attack_ability >= nowCastle->blueWarrior->blood;
                }
                if(!judge1&&!judge2){
                    if(nowCastle->redWarrior->bombs.totalnum>0){
                        if(nowCastle->blueWarrior->swords.totalnum>0){
                            if(nowCastle->blueWarrior->attack_ability/2+nowCastle->blueWarrior->swords.attack_ability >= nowCastle->redWarrior->blood){
                                std::printf("%03d:%02d red %s %d used a bomb and killed blue %s %d\n",gametime / 60, gametime % 60,
                                       nowCastle->redWarrior->name,nowCastle->redWarrior->ID,
                                       nowCastle->blueWarrior->name,nowCastle->blueWarrior->ID);
                                delete nowCastle->blueWarrior;
                                nowCastle->blueWarrior = nullptr;
                                delete nowCastle->redWarrior;
                                nowCastle->redWarrior = nullptr;
                                continue;
                            }
                        }
                        else{
                            if (nowCastle->blueWarrior->attack_ability/2 >= nowCastle->redWarrior->blood)
                            {
                                std::printf("%03d:%02d red %s %d used a bomb and killed blue %s %d\n", gametime / 60, gametime % 60,
                                       nowCastle->redWarrior->name, nowCastle->redWarrior->ID,
                                       nowCastle->blueWarrior->name, nowCastle->blueWarrior->ID);
                                delete nowCastle->blueWarrior;
                                nowCastle->blueWarrior = nullptr;
                                delete nowCastle->redWarrior;
                                nowCastle->redWarrior = nullptr;
                                continue;
                            }
                        }
                    }
                }
                if(nowCastle->blueWarrior->bombs.totalnum>0){
                    if (nowCastle->redWarrior->swords.totalnum > 0)
                    {
                        if (nowCastle->redWarrior->attack_ability + nowCastle->redWarrior->swords.attack_ability >= nowCastle->blueWarrior->blood)
                        {
                            std::printf("%03d:%02d blue %s %d used a bomb and killed red %s %d\n", gametime / 60, gametime % 60,
                                   nowCastle->blueWarrior->name, nowCastle->blueWarrior->ID,
                                   nowCastle->redWarrior->name, nowCastle->redWarrior->ID);
                            delete nowCastle->blueWarrior;
                            nowCastle->blueWarrior = nullptr;
                            delete nowCastle->redWarrior;
                            nowCastle->redWarrior = nullptr;
                            continue;
                        }
                    }
                    else
                    {
                        if (nowCastle->redWarrior->attack_ability >= nowCastle->blueWarrior->blood)
                        {
                            std::printf("%03d:%02d blue %s %d used a bomb and killed red %s %d\n", gametime / 60, gametime % 60,
                                   nowCastle->blueWarrior->name, nowCastle->blueWarrior->ID,
                                   nowCastle->redWarrior->name, nowCastle->redWarrior->ID);
                            delete nowCastle->blueWarrior;
                            nowCastle->blueWarrior = nullptr;
                            delete nowCastle->redWarrior;
                            nowCastle->redWarrior = nullptr;
                            continue;
                        }
                    }
                }
            }
            else if(nowCastle->flag=='b'||(nowCastle->flag=='n'&&nowCastle->ID%2==0))
            {
                bool judge1 = (strcmp(nowCastle->redWarrior->name, "ninja") == 0);
                bool judge2 = 0;
                if (nowCastle->blueWarrior->swords.totalnum > 0)
                {
                    judge2 = nowCastle->blueWarrior->swords.attack_ability + nowCastle->blueWarrior->attack_ability >= nowCastle->redWarrior->blood;
                }
                else
                {
                    judge2 = nowCastle->blueWarrior->attack_ability >= nowCastle->redWarrior->blood;
                }
                if(!judge1&&!judge2){
                    if (nowCastle->blueWarrior->bombs.totalnum > 0)
                    {
                        if (nowCastle->redWarrior->swords.totalnum > 0)
                        {
                            if (nowCastle->redWarrior->attack_ability/2 + nowCastle->redWarrior->swords.attack_ability >= nowCastle->blueWarrior->blood)
                            {
                                std::printf("%03d:%02d blue %s %d used a bomb and killed red %s %d\n", gametime / 60, gametime % 60,
                                       nowCastle->blueWarrior->name, nowCastle->blueWarrior->ID,
                                       nowCastle->redWarrior->name, nowCastle->redWarrior->ID);
                                delete nowCastle->blueWarrior;
                                nowCastle->blueWarrior = nullptr;
                                delete nowCastle->redWarrior;
                                nowCastle->redWarrior = nullptr;
                                continue;
                            }
                        }
                        else
                        {
                            if (nowCastle->redWarrior->attack_ability/2 >= nowCastle->blueWarrior->blood)
                            {
                                std::printf("%03d:%02d blue %s %d used a bomb and killed red %s %d\n", gametime / 60, gametime % 60,
                                       nowCastle->blueWarrior->name, nowCastle->blueWarrior->ID,
                                       nowCastle->redWarrior->name, nowCastle->redWarrior->ID);
                                delete nowCastle->blueWarrior;
                                nowCastle->blueWarrior = nullptr;
                                delete nowCastle->redWarrior;
                                nowCastle->redWarrior = nullptr;
                                continue;
                            }
                        }
                    }
                }
                if (nowCastle->redWarrior->bombs.totalnum > 0)
                {
                    if (nowCastle->blueWarrior->swords.totalnum > 0)
                    {
                        if (nowCastle->blueWarrior->attack_ability + nowCastle->blueWarrior->swords.attack_ability >= nowCastle->redWarrior->blood)
                        {
                            std::printf("%03d:%02d red %s %d used a bomb and killed blue %s %d\n", gametime / 60, gametime % 60,
                                   nowCastle->redWarrior->name, nowCastle->redWarrior->ID,
                                   nowCastle->blueWarrior->name, nowCastle->blueWarrior->ID);
                            delete nowCastle->blueWarrior;
                            nowCastle->blueWarrior = nullptr;
                            delete nowCastle->redWarrior;
                            nowCastle->redWarrior = nullptr;
                            continue;
                        }
                    }
                    else
                    {
                        if (nowCastle->blueWarrior->attack_ability >= nowCastle->redWarrior->blood)
                        {
                            std::printf("%03d:%02d red %s %d used a bomb and killed blue %s %d\n", gametime / 60, gametime % 60,
                                   nowCastle->redWarrior->name, nowCastle->redWarrior->ID,
                                   nowCastle->blueWarrior->name, nowCastle->blueWarrior->ID);
                            delete nowCastle->blueWarrior;
                            nowCastle->blueWarrior = nullptr;
                            delete nowCastle->redWarrior;
                            nowCastle->redWarrior = nullptr;
                            continue;
                        }
                    }
                }
            }
        }
    }
}
int main(){
    int n = 0;
    cin >> n;
    int n1 = n;
    while(n--){
        gametime = 0;
        gameover = 0;
        castle castles[25];
        int blood = 0, citys = 0, arrow_atk = 0, dloyalty = 0, span = 0,
            db = 0, nb = 0, ib = 0, lb = 0, wb = 0,
            datk = 0, natk = 0, iatk = 0, latk = 0, watk = 0;
        scanf("%d%d%d%d%d%d%d%d%d%d%d%d%d%d%d",&blood,&citys,&arrow_atk,&dloyalty,&span,&db,&nb,&ib,&lb,&wb,&datk,&natk,&iatk,&latk,&watk);
        for (int i = 0; i <= citys + 1;++i){
            castles[i].ID = i;
            if(i>=1&&i<=citys){
                castles[i].flag = 'n';
                castles[i].nowBetter = 'n';
            }
            if(i==0)
                castles[i].preCastle = nullptr;
            else
                castles[i].preCastle = castles + i - 1;
            if(i==citys+1)
                castles[i].nextCastle = nullptr;
            else
                castles[i].nextCastle = castles + i + 1;
            
        }
        redtroop::blood = blood;
        redtroop::dragon_attr[0] = db;
        redtroop::dragon_attr[1] = datk;
        redtroop::ninja_attr[0] = nb;
        redtroop::ninja_attr[1] = natk;
        redtroop::iceman_attr[0] = ib;
        redtroop::iceman_attr[1] = iatk;
        redtroop::lion_attr[0] = lb;
        redtroop::lion_attr[1] = latk;
        redtroop::wolf_attr[0] = wb;
        redtroop::wolf_attr[1] = watk;
        bluetroop::blood = blood;
        bluetroop::dragon_attr[0] = db;
        bluetroop::dragon_attr[1] = datk;
        bluetroop::ninja_attr[0] = nb;
        bluetroop::ninja_attr[1] = natk;
        bluetroop::iceman_attr[0] = ib;
        bluetroop::iceman_attr[1] = iatk;
        bluetroop::lion_attr[0] = lb;
        bluetroop::lion_attr[1] = latk;
        bluetroop::wolf_attr[0] = wb;
        bluetroop::wolf_attr[1] = watk;
        redtroop red;
        bluetroop blue;
        lion::fear = dloyalty;
        arrow::arrow_atk = arrow_atk;
        std::cout << "Case " << n1 - n <<":"<< endl;
        while(gametime<=span){
            if(gametime%60==0){
                if(red.blood>=red.sequence[(red.loopptr)%5]->blood){
                    red.IDofNowMakingWarrior += 1;
                    warrior &tmp = *red.sequence[(red.loopptr) % 5];
                    std::printf("%03d:%02d red %s %d born\n",gametime/60,gametime%60,tmp.name,red.IDofNowMakingWarrior);
                    if (strcmp(tmp.name,"dragon")==0)
                    {
                        red.blood -= redtroop::dragon_attr[0];
                        dragon *pdragon = new dragon('r', red.IDofNowMakingWarrior);
                        pdragon->morale = float(red.blood) / redtroop::dragon_attr[0];
                        std::printf("Its morale is %.2f\n", pdragon->morale);
                        castles[0].redWarrior_tmp = pdragon;
                    }
                    else if (strcmp(tmp.name,"ninja")==0)
                    {
                        red.blood -= redtroop::ninja_attr[0];
                        ninja *pninja = new ninja('r', red.IDofNowMakingWarrior);
                        castles[0].redWarrior_tmp = pninja;
                    }
                    else if (strcmp(tmp.name,"iceman")==0)
                    {
                        red.blood -= redtroop::iceman_attr[0];
                        iceman *piceman = new iceman('r', red.IDofNowMakingWarrior);
                        castles[0].redWarrior_tmp = piceman;
                    }
                    else if (strcmp(tmp.name,"lion")==0)
                    {
                        red.blood -= redtroop::lion_attr[0];
                        lion *plion = new lion('r', red.IDofNowMakingWarrior);
                        castles[0].redWarrior_tmp =plion;
                        std::printf("Its loyalty is %d\n",plion->loyalty);
                    }
                    else{
                        red.blood -= redtroop::wolf_attr[0];
                        wolf *pwolf = new wolf('r', red.IDofNowMakingWarrior);
                        castles[0].redWarrior_tmp = pwolf;
                    }
                    red.loopptr = (red.loopptr+ 1) % 5;
                }
                
                if (blue.blood >= blue.sequence[(blue.loopptr) % 5]->blood)
                {
                    blue.IDofNowMakingWarrior += 1;
                    warrior &tmp = *blue.sequence[(blue.loopptr) % 5];
                    std::printf("%03d:%02d blue %s %d born\n",
                           gametime/60,gametime%60, tmp.name, blue.IDofNowMakingWarrior);
                    if (strcmp(tmp.name, "dragon") == 0)
                    {
                        blue.blood -= bluetroop::dragon_attr[0];
                        dragon *pdragon = new dragon('b', blue.IDofNowMakingWarrior);
                        pdragon->morale = float(blue.blood) / bluetroop::dragon_attr[0];
                        std::printf("Its morale is %.2f\n", pdragon->morale);
                        castles[citys + 1].blueWarrior = pdragon;
                    }
                    else if (strcmp(tmp.name, "ninja") == 0)
                    {
                        blue.blood -= bluetroop::ninja_attr[0];
                        ninja *pninja = new ninja('b', blue.IDofNowMakingWarrior);
                        castles[citys+1].blueWarrior = pninja;
                    }
                    else if (strcmp(tmp.name, "iceman") == 0)
                    {
                        blue.blood -= bluetroop::iceman_attr[0];
                        iceman *piceman = new iceman('b', blue.IDofNowMakingWarrior);
                        castles[citys + 1].blueWarrior = piceman;
                    }
                    else if (strcmp(tmp.name, "lion") == 0)
                    {
                        blue.blood -= bluetroop::lion_attr[0];
                        lion *plion = new lion('b', blue.IDofNowMakingWarrior);
                        castles[citys + 1].blueWarrior = plion;
                        std::printf("Its loyalty is %d\n", plion->loyalty);
                    }
                    else
                    {
                        blue.blood -= bluetroop::wolf_attr[0];
                        wolf *pwolf = new wolf('b', blue.IDofNowMakingWarrior);
                        castles[citys+1].blueWarrior = pwolf;
                    }
                    blue.loopptr = (blue.loopptr+ 1) % 5;
                }
                
            }
            else if(gametime%60==5){
                for (int i = 0; i <= citys + 1; ++i)
                {
                    if(i==0){
                        if(castles[i].redWarrior_tmp&&strcmp(castles[i].redWarrior_tmp->name,"lion")==0){
                            lion *plion = (lion *)castles[i].redWarrior_tmp;
                            if (plion->loyalty <= 0)
                            {
                                std::printf("%03d:%02d red lion %d ran away\n", gametime / 60, gametime % 60, plion->ID);
                                delete castles[i].redWarrior_tmp;
                                castles[i].redWarrior_tmp = nullptr;
                            }
                        }
                    }
                    if (castles[i].redWarrior != nullptr)
                    {
                        if (strcmp(castles[i].redWarrior->name, "lion") == 0)
                        {
                            lion *plion = (lion *)castles[i].redWarrior;
                            if (plion->loyalty <= 0)
                            {
                                std::printf("%03d:%02d red lion %d ran away\n", gametime / 60, gametime % 60, plion->ID);
                                delete castles[i].redWarrior;
                                castles[i].redWarrior = nullptr;
                            }
                        }
                    }
                    if (castles[i].blueWarrior != nullptr)
                    {
                        if (strcmp(castles[i].blueWarrior->name, "lion") == 0)
                        {
                            lion *plion = (lion *)castles[i].blueWarrior;
                            if (plion->loyalty <= 0)
                            {
                                std::printf("%03d:%02d blue lion %d ran away\n", gametime / 60, gametime % 60, plion->ID);
                                delete castles[i].blueWarrior;
                                castles[i].blueWarrior = nullptr;
                            }
                        }
                    }
                }
            }
            else if(gametime%60==10){
                for (int i = 0; i <= citys + 1;++i){
                    redmarch(castles + i,citys);
                    bluemarch(castles + i,citys);
                }
                if(red.win==2||blue.win==2){
                    break;
                }
            }
            else if(gametime%60==20){
                for (int i = 0; i <= citys + 1;++i){
                    castles[i].blood += 10;
                }
            }
            else if(gametime%60==30){
                for (int i = 1; i <= citys;++i){
                    if(castles[i].redWarrior!=nullptr&&castles[i].blueWarrior==nullptr)
                    {
                        std::printf("%03d:%02d red %s %d earned %d elements for his headquarter\n", gametime / 60, gametime % 60,
                               castles[i].redWarrior->name, castles[i].redWarrior->ID,castles[i].blood);
                        red.blood += castles[i].blood;
                        castles[i].blood = 0;
                    }
                    else if(castles[i].redWarrior==nullptr&&castles[i].blueWarrior!=nullptr){
                        std::printf("%03d:%02d blue %s %d earned %d elements for his headquarter\n", gametime / 60, gametime % 60,
                               castles[i].blueWarrior->name, castles[i].blueWarrior->ID,castles[i].blood);
                        blue.blood += castles[i].blood;
                        castles[i].blood = 0;
                    }
                }
            }
            else if(gametime%60==35){
                sneakArrowAttack(castles, citys);
            }
            else if(gametime%60==38){
                perishBombAttack(castles, citys);
            }
            else if(gametime%60==40){
                for (int i = 1; i <= citys;++i){
                    if(castles[i].blueWarrior&&castles[i].redWarrior){
                        if (strcmp(castles[i].redWarrior->name, "lion") == 0)
                        {
                            lion *plion = (lion *)castles[i].redWarrior;
                            plion->blood_copy = max(0,plion->blood);
                        }
                        if (strcmp(castles[i].blueWarrior->name, "lion") == 0)
                        {
                            lion *plion = (lion *)castles[i].blueWarrior;
                            plion->blood_copy = max(0,plion->blood);
                        }
                        castles[i].fight();
                        castles[i].printOutcome();
                    }
                }
                for (int i = citys; i >= 1;--i){
                    if(castles[i].redWarrior&&castles[i].blueWarrior){
                        if(red.blood<8)
                            break;
                        if(castles[i].redWarrior&&castles[i].blueWarrior&&castles[i].redWarrior->blood>0&&castles[i].blueWarrior->blood<=0){
                            castles[i].redWarrior->blood += 8;
                            red.blood -= 8;
                        }
                    }
                }
                for (int i = 1; i <= citys;++i){
                    if(castles[i].redWarrior&&castles[i].blueWarrior){
                        if (blue.blood < 8)
                            break;
                        if (castles[i].redWarrior && castles[i].blueWarrior && castles[i].redWarrior->blood <= 0 && castles[i].blueWarrior->blood > 0)
                        {
                            castles[i].blueWarrior->blood += 8;
                            blue.blood -= 8;
                        }
                    }
                }
                for (int i = 1; i <= citys;++i){
                    if(castles[i].redWarrior&&castles[i].blueWarrior&&castles[i].redWarrior->blood>0&&castles[i].blueWarrior->blood<=0){
                        red.blood += castles[i].blood;
                        castles[i].blood =0;
                        delete castles[i].blueWarrior;
                        castles[i].blueWarrior = nullptr;
                    }
                    else if (castles[i].redWarrior && castles[i].blueWarrior && castles[i].redWarrior->blood <= 0 && castles[i].blueWarrior->blood > 0){
                        blue.blood += castles[i].blood;
                        castles[i].blood = 0;
                        delete castles[i].redWarrior;
                        castles[i].redWarrior = nullptr;
                    }
                }
            }
            else if(gametime%60==50){
                std::printf("%03d:%02d %d elements in red headquarter\n", gametime / 60, gametime % 60, red.blood);
                std::printf("%03d:%02d %d elements in blue headquarter\n", gametime / 60, gametime % 60, blue.blood);
            }
            else if(gametime%60==55){
                for (int i = 0; i <= citys + 1;++i){
                    if(castles[i].redWarrior){
                        std::printf("%03d:%02d red %s %d has ", gametime / 60, gametime % 60,castles[i].redWarrior->name,castles[i].redWarrior->ID);
                        bool tmp = 0;
                        if(castles[i].redWarrior->arrows.totalnum>0){
                            std::printf("arrow(%d)", 3 - castles[i].redWarrior->arrows.used_time);
                            tmp = 1;
                        }
                        if(castles[i].redWarrior->bombs.totalnum>0){
                            if(tmp)
                                std::printf(",");
                            else
                                tmp = 1;
                            std::printf("bomb");
                        }
                        if(castles[i].redWarrior->swords.totalnum>0){
                            if(tmp)
                                std::printf(",");
                            else
                                tmp = 1;
                            std::printf("sword(%d)", castles[i].redWarrior->swords.attack_ability);
                        }
                        if(!tmp)
                            std::printf("no weapon");
                        std::printf("\n");
                    }
                }
                if (castles[citys+1].redWarrior_tmp)
                {
                    std::printf("%03d:%02d red %s %d has ", gametime / 60, gametime % 60, castles[citys+1].redWarrior_tmp->name, castles[citys+1].redWarrior_tmp->ID);
                    bool tmp = 0;
                    if (castles[citys+1].redWarrior_tmp->arrows.totalnum > 0)
                    {
                        std::printf("arrow(%d)", 3 - castles[citys+1].redWarrior_tmp->arrows.used_time);
                        tmp = 1;
                    }
                    if (castles[citys+1].redWarrior_tmp->bombs.totalnum > 0)
                    {
                        if (tmp)
                            std::printf(",");
                        else
                            tmp = 1;
                        std::printf("bomb");
                    }
                    if (castles[citys+1].redWarrior_tmp->swords.totalnum > 0)
                    {
                        if (tmp)
                            std::printf(",");
                        else
                            tmp = 1;
                        std::printf("sword(%d)", castles[citys+1].redWarrior_tmp->swords.attack_ability);
                    }
                    if (!tmp)
                        std::printf("no weapon");
                    std::printf("\n");
                }
                if (castles[0].blueWarrior_tmp)
                {
                    std::printf("%03d:%02d blue %s %d has ", gametime / 60, gametime % 60, castles[0].blueWarrior_tmp->name, castles[0].blueWarrior_tmp->ID);
                    bool tmp = 0;
                    if (castles[0].blueWarrior_tmp->arrows.totalnum > 0)
                    {
                        std::printf("arrow(%d)", 3 - castles[0].blueWarrior_tmp->arrows.used_time);
                        tmp = 1;
                    }
                    if (castles[0].blueWarrior_tmp->bombs.totalnum > 0)
                    {
                        if (tmp)
                            std::printf(",");
                        else
                            tmp = 1;
                        std::printf("bomb");
                    }
                    if (castles[0].blueWarrior_tmp->swords.totalnum > 0)
                    {
                        if (tmp)
                            std::printf(",");
                        else
                            tmp = 1;
                        std::printf("sword(%d)", castles[0].blueWarrior_tmp->swords.attack_ability);
                    }
                    if (!tmp)
                    {
                        std::printf("no weapon");
                    }
                    std::printf("\n");
                }
                for (int i = 0; i <= citys + 1;++i){
                    if (castles[i].blueWarrior){
                        std::printf("%03d:%02d blue %s %d has ", gametime / 60, gametime % 60, castles[i].blueWarrior->name, castles[i].blueWarrior->ID);
                        bool tmp = 0;
                        if (castles[i].blueWarrior->arrows.totalnum > 0){
                            std::printf("arrow(%d)", 3 - castles[i].blueWarrior->arrows.used_time);
                            tmp = 1;
                        }
                        if (castles[i].blueWarrior->bombs.totalnum > 0){
                            if(tmp)
                                std::printf(",");
                            else
                                tmp = 1;
                            std::printf("bomb");
                        }
                        if (castles[i].blueWarrior->swords.totalnum > 0){
                            if(tmp)
                                std::printf(",");
                            else
                                tmp = 1;
                            std::printf("sword(%d)", castles[i].blueWarrior->swords.attack_ability);
                        }
                        if(!tmp){
                            std::printf("no weapon");
                        }
                        std::printf("\n");
                    }
                }
            }
            ++gametime;
        }
        for (int i = 0; i <= citys + 1;++i){
            if(castles[i].redWarrior){
                delete castles[i].redWarrior;
            }
            if(castles[i].blueWarrior){
                delete castles[i].blueWarrior;
            }
            if(castles[i].redWarrior_tmp)
                delete castles[i].redWarrior_tmp;
            if(castles[i].blueWarrior_tmp)
                delete castles[i].blueWarrior_tmp;
        }
    }
    //system("pause");
    return 0;
}
