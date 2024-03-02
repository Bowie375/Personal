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
    weapon(const char *Name, int ATK) : attack_ability(ATK)
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
    sword(int atk) : weapon("sword", atk) {}
    sword(const sword &sword1) : weapon(sword1.name, sword1.attack_ability) {}
    static void slash(warrior *attacker, warrior *offender);
    virtual ~sword(){}
};
class bomb : public weapon
{
public:
    bomb() : weapon("bomb", 0){}
    bomb(int atk) : weapon("bomb", atk) {}
    bomb(const bomb &bomb1) : weapon(bomb1.name, bomb1.attack_ability){}
    static void explode(warrior *attacker, warrior *offender);
    virtual ~bomb(){}
};
class arrow : public weapon
{
public:
    int usedZeroNum;
    int usedOnceNum;
    arrow():weapon("arrow",0){}
    arrow(int atk) : weapon("sword", atk){}
    arrow(const arrow &arrow1) : weapon(arrow1.name, arrow1.attack_ability){}
    static void shoot(warrior *attacker, warrior *offender);
    virtual ~arrow() {}
};

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
        int nowWeapon[2];
        warrior(const char* Name){
            strcpy(name, Name);
        }
        virtual ~warrior(){}
        void robTrophy(warrior*losedWarrior){
            while(totalWeaponNum<10&&losedWarrior->totalWeaponNum>0){
                if(losedWarrior->swords.totalnum>0){
                    losedWarrior->totalWeaponNum -= 1;
                    losedWarrior->swords.totalnum -= 1;
                    totalWeaponNum += 1;
                    swords.totalnum += 1;
                }
                else if (losedWarrior->bombs.totalnum > 0)
                {
                    losedWarrior->totalWeaponNum -= 1;
                    losedWarrior->bombs.totalnum -= 1;
                    totalWeaponNum += 1;
                    bombs.totalnum += 1;
                }
                else if (losedWarrior->arrows.totalnum > 0)
                {
                    if(losedWarrior->arrows.usedZeroNum>0){
                        losedWarrior->totalWeaponNum -= 1;
                        losedWarrior->arrows.usedZeroNum -= 1;
                        losedWarrior->arrows.totalnum -= 1;
                        totalWeaponNum += 1;
                        arrows.usedZeroNum += 1;
                        arrows.totalnum += 1;
                    }
                    else{
                        losedWarrior->totalWeaponNum -= 1;
                        losedWarrior->arrows.usedOnceNum -= 1;
                        losedWarrior->arrows.totalnum -= 1;
                        totalWeaponNum += 1;
                        arrows.usedOnceNum += 1;
                        arrows.totalnum += 1;
                    }
                }
            }
        }
};

void sword::slash(warrior *attacker, warrior *offender)
{
    offender->blood = max(0, offender->blood - attacker->attack_ability * 2 / 10);
}
void bomb::explode(warrior *attacker, warrior *offender)
{
    if (strcmp(attacker->name, "ninja") != 0)
    {
            attacker->blood = max(attacker->blood - attacker->attack_ability * 4 / 10 / 2, 0);
    }
    offender->blood = max(0, offender->blood - attacker->attack_ability * 4 / 10);
}
void arrow::shoot(warrior *attacker, warrior *offender)
{
    offender->blood = max(0, offender->blood - attacker->attack_ability * 3 / 10);
}

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
        iceman(char troopColor, int id);
        iceman() :warrior("iceman") {}
        ~iceman(){}
};
class lion:public warrior{
    public:
        int loyalty;
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
        void robWeapon(warrior* opponent){
            if(strcmp(name,opponent->name)==0)
                return;
            if(opponent->totalWeaponNum==0)
                return;
            if (opponent->swords.totalnum > 0)
            {
                while(totalWeaponNum<10&&opponent->swords.totalnum>0){
                    opponent->totalWeaponNum -= 1;
                    opponent->swords.totalnum -= 1;
                    totalWeaponNum += 1;
                    swords.totalnum += 1;
                }
            }
            else if (opponent->bombs.totalnum > 0)
            {
                while (totalWeaponNum < 10 && opponent->bombs.totalnum > 0)
                {
                    opponent->totalWeaponNum -= 1;
                    opponent->bombs.totalnum -= 1;
                    totalWeaponNum += 1;
                    bombs.totalnum += 1;
                }
            }
            else if (opponent->arrows.totalnum > 0)
            {
                while (totalWeaponNum < 10 && opponent->arrows.totalnum > 0)
                {
                    if (opponent->arrows.usedZeroNum > 0)
                    {
                        opponent->totalWeaponNum -= 1;
                        opponent->arrows.usedZeroNum -= 1;
                        opponent->arrows.totalnum -= 1;
                        totalWeaponNum += 1;
                        arrows.usedZeroNum += 1;
                        arrows.totalnum += 1;
                    }
                    else
                    {
                        opponent->totalWeaponNum -= 1;
                        opponent->arrows.usedOnceNum -= 1;
                        opponent->arrows.totalnum -= 1;
                        totalWeaponNum += 1;
                        arrows.usedOnceNum += 1;
                        arrows.totalnum += 1;
                    }
                }
            }
        }
};

class troop{
    public:
        int IDofNowMakingWarrior;
        int loopptr;
        bool stopmaking;
        bool win;
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
        arrows.totalnum = 0;
        arrows.usedOnceNum = 0;
        arrows.usedZeroNum = 0;
        bombs.totalnum = 0;
        swords.totalnum = 0;
        totalWeaponNum = 0;
        switch (ID % 3)
        {
        case 0:
            swords.totalnum += 1;
            totalWeaponNum += 1;
            swords.attack_ability = attack_ability * 2 / 10;
            nowWeapon[0] = 0;
            nowWeapon[1] = 0;
            break;
        case 1:
            bombs.totalnum += 1;
            totalWeaponNum += 1;
            bombs.attack_ability = attack_ability * 4 / 10;
            nowWeapon[0] = 1;
            nowWeapon[1] = 0;
            break;
        case 2:
            arrows.totalnum += 1;
            arrows.usedZeroNum += 1;
            totalWeaponNum += 1;
            arrows.attack_ability = attack_ability * 3 / 10;
            nowWeapon[0] = 2;
            nowWeapon[1] = 0;
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
        arrows.totalnum = 0;
        arrows.usedOnceNum = 0;
        arrows.usedZeroNum = 0;
        bombs.totalnum = 0;
        swords.totalnum = 0;
        totalWeaponNum = 0;
        switch (ID % 3)
        {
        case 0:
            swords.totalnum += 1;
            bombs.totalnum += 1;
            totalWeaponNum += 2;
            swords.attack_ability = attack_ability * 2 / 10;
            bombs.attack_ability = attack_ability * 4 / 10;
            nowWeapon[0] = 0;
            nowWeapon[1] = 0;
            break;
        case 1:
            bombs.totalnum += 1;
            arrows.totalnum += 1;
            arrows.usedZeroNum += 1;
            totalWeaponNum += 2;
            bombs.attack_ability = attack_ability * 4 / 10;
            arrows.attack_ability = attack_ability * 3 / 10;
            nowWeapon[0] = 1;
            nowWeapon[1] = 0;
            break;
        case 2:
            swords.totalnum += 1;
            arrows.totalnum += 1;
            arrows.usedZeroNum += 1;
            totalWeaponNum += 2;
            swords.attack_ability = attack_ability * 2 / 10;
            arrows.attack_ability = attack_ability * 3 / 10;
            nowWeapon[0] = 0;
            nowWeapon[1] = 0;
            break;
        }
}
iceman::iceman(char troopColor, int id) : warrior("iceman")
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
        arrows.totalnum = 0;
        arrows.usedOnceNum = 0;
        arrows.usedZeroNum = 0;
        bombs.totalnum = 0;
        swords.totalnum = 0;
        totalWeaponNum = 0;
        switch (ID % 3)
        {
        case 0:
            swords.totalnum += 1;
            totalWeaponNum += 1;
            swords.attack_ability = attack_ability * 2 / 10;
            nowWeapon[0] = 0;
            nowWeapon[1] = 0;
            break;
        case 1:
            bombs.totalnum += 1;
            totalWeaponNum += 1;
            bombs.attack_ability = attack_ability * 4 / 10;
            nowWeapon[0] = 1;
            nowWeapon[1] = 0;
            break;
        case 2:
            arrows.totalnum += 1;
            arrows.usedZeroNum += 1;
            totalWeaponNum += 1;
            arrows.attack_ability = attack_ability * 3 / 10;
            nowWeapon[0] = 2;
            nowWeapon[1] = 0;
            break;
        }
}
lion::lion(char troopColor, int id) : warrior("lion")
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
        arrows.totalnum = 0;
        arrows.usedOnceNum = 0;
        arrows.usedZeroNum = 0;
        bombs.totalnum = 0;
        swords.totalnum = 0;
        totalWeaponNum = 0;
        switch (ID % 3)
        {
        case 0:
            swords.totalnum += 1;
            totalWeaponNum += 1;
            swords.attack_ability = attack_ability * 2 / 10;
            nowWeapon[0] = 0;
            nowWeapon[1] = 0;
            break;
        case 1:
            bombs.totalnum += 1;
            totalWeaponNum += 1;
            bombs.attack_ability = attack_ability * 4 / 10;
            nowWeapon[0] = 1;
            nowWeapon[1] = 0;
            break;
        case 2:
            arrows.totalnum += 1;
            arrows.usedZeroNum += 1;
            totalWeaponNum += 1;
            arrows.attack_ability = attack_ability * 3 / 10;
            nowWeapon[0] = 2;
            nowWeapon[1] = 0;
            break;
        }
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
        arrows.totalnum = 0;
        arrows.usedOnceNum = 0;
        arrows.usedZeroNum = 0;
        bombs.totalnum = 0;
        swords.totalnum = 0;
        totalWeaponNum = 0;
}

class castle{
public:
    int ID;
    castle *preCastle;
    castle *nextCastle;
    warrior *redWarrior;
    warrior *redWarrior_tmp;
    warrior *blueWarrior;
    castle(){
        redWarrior = nullptr;
        blueWarrior = nullptr;
        redWarrior_tmp = nullptr;
    }
    ~castle(){

    }
    void prepareWeapon(){
        if(redWarrior->totalWeaponNum>0){
            if(redWarrior->swords.totalnum>0){
                redWarrior->nowWeapon[0] = 0;
            }
            else if(redWarrior->bombs.totalnum>0){
                redWarrior->nowWeapon[0] = 1;
            }
            else if(redWarrior->arrows.usedOnceNum>0){
                redWarrior->nowWeapon[0] = 2;
            }
            else if(redWarrior->arrows.usedZeroNum>0){
                redWarrior->nowWeapon[0] = 3;
            }
            redWarrior->nowWeapon[1] = 0;
        }
        if (blueWarrior->totalWeaponNum > 0)
        {
            if (blueWarrior->swords.totalnum > 0)
            {
                blueWarrior->nowWeapon[0] = 0;
            }
            else if (blueWarrior->bombs.totalnum > 0)
            {
                blueWarrior->nowWeapon[0] = 1;
            }
            else if (blueWarrior->arrows.usedOnceNum > 0)
            {
                blueWarrior->nowWeapon[0] = 2;
            }
            else if (blueWarrior->arrows.usedZeroNum > 0)
            {
                blueWarrior->nowWeapon[0] = 3;
            }
            blueWarrior->nowWeapon[1] = 0;
        }
    }
    void wolfRob(){
        if (strcmp(redWarrior->name, "wolf") == 0)
        {
            wolf *redWarrior_tmp = (wolf *)redWarrior;
            int sword0 = redWarrior_tmp->swords.totalnum, bomb0 = redWarrior_tmp->bombs.totalnum, arrow0 = redWarrior->arrows.totalnum;
            redWarrior_tmp->robWeapon(blueWarrior);
            int robSword = redWarrior_tmp->swords.totalnum - sword0;
            int robBomb = redWarrior_tmp->bombs.totalnum - bomb0;
            int robArrow = redWarrior_tmp->arrows.totalnum - arrow0;
            if (robSword || robBomb || robArrow)
            {
                printf("%03d:%02d red wolf %d took ", gametime / 60, gametime % 60, redWarrior->ID);
                if (robSword){
                    printf("%d sword ", robSword);
                }
                else if (robBomb){
                    printf("%d bomb ", robBomb);
                }
                if (robArrow){
                    printf("%d arrow ", robArrow);
                }
                printf("from blue %s %d in city %d\n", blueWarrior->name, blueWarrior->ID, ID);
            }
        }
        if (strcmp(blueWarrior->name, "wolf") == 0)
        {
            wolf *blueWarrior_tmp = (wolf *)blueWarrior;
            int sword0 = blueWarrior_tmp->swords.totalnum, bomb0 = blueWarrior_tmp->bombs.totalnum, arrow0 = blueWarrior->arrows.totalnum;
            blueWarrior_tmp->robWeapon(redWarrior);
            int robSword = blueWarrior_tmp->swords.totalnum - sword0;
            int robBomb = blueWarrior_tmp->bombs.totalnum - bomb0;
            int robArrow = blueWarrior_tmp->arrows.totalnum - arrow0;
            if (robSword || robBomb || robArrow)
            {
                printf("%03d:%02d blue wolf %d took ", gametime / 60, gametime % 60, blueWarrior->ID);
                if (robSword)
                {
                    printf("%d sword ", robSword);
                }
                else if (robBomb)
                {
                    printf("%d bomb ", robBomb);
                }
                if (robArrow)
                {
                    printf("%d arrow ", robArrow);
                }
                printf("from red %s %d in city %d\n", redWarrior->name, redWarrior->ID, ID);
            }
        }
    }
    void redInCharge(){
        if (redWarrior->totalWeaponNum > 0)
        {
            if (redWarrior->nowWeapon[0] == 0)
            {
                sword::slash(redWarrior, blueWarrior);
                if (redWarrior->nowWeapon[1] < redWarrior->swords.totalnum - 1)
                {
                    redWarrior->nowWeapon[1] += 1;
                }
                else
                {
                    if (redWarrior->bombs.totalnum > 0)
                    {
                        redWarrior->nowWeapon[0] = 1;
                    }
                    else if (redWarrior->arrows.usedOnceNum > 0)
                    {
                        redWarrior->nowWeapon[0] = 2;
                    }
                    else if (redWarrior->arrows.usedZeroNum > 0)
                    {
                        redWarrior->nowWeapon[0] = 3;
                    }
                    redWarrior->nowWeapon[1] = 0;
                }
            }
            else if (redWarrior->nowWeapon[0] == 1)
            {
                bomb::explode(redWarrior, blueWarrior);
                redWarrior->totalWeaponNum -= 1;
                redWarrior->bombs.totalnum -= 1;
                if (redWarrior->bombs.totalnum > 0)
                {
                    redWarrior->nowWeapon[1] = 0;
                }
                else
                {
                    if (redWarrior->arrows.usedOnceNum > 0)
                    {
                        redWarrior->nowWeapon[0] = 2;
                    }
                    else if (redWarrior->arrows.usedZeroNum > 0)
                    {
                        redWarrior->nowWeapon[0] = 3;
                    }
                    else if (redWarrior->swords.totalnum > 0)
                    {
                        redWarrior->nowWeapon[0] = 0;
                    }
                    redWarrior->nowWeapon[1] = 0;
                }
            }
            else if (redWarrior->nowWeapon[0] == 2)
            {
                arrow::shoot(redWarrior, blueWarrior);
                redWarrior->totalWeaponNum -= 1;
                redWarrior->arrows.totalnum -= 1;
                redWarrior->arrows.usedOnceNum -= 1;
                if (redWarrior->arrows.usedOnceNum > 0)
                {
                    redWarrior->nowWeapon[1] = 0;
                }
                else
                {
                    if (redWarrior->arrows.usedZeroNum > 0)
                    {
                        redWarrior->nowWeapon[0] = 3;
                    }
                    else if (redWarrior->swords.totalnum > 0)
                    {
                        redWarrior->nowWeapon[0] = 0;
                    }
                    else if (redWarrior->bombs.totalnum > 0)
                    {
                        redWarrior->nowWeapon[0] = 1;
                    }
                    redWarrior->nowWeapon[1] = 0;
                }
            }
            else if (redWarrior->nowWeapon[0] == 3)
            {
                arrow::shoot(redWarrior, blueWarrior);
                redWarrior->arrows.usedZeroNum -= 1;
                redWarrior->arrows.usedOnceNum += 1;
                if (redWarrior->arrows.usedZeroNum > 0)
                {
                    redWarrior->nowWeapon[1] = 0;
                }
                else
                {
                    if (redWarrior->swords.totalnum > 0)
                    {
                        redWarrior->nowWeapon[0] = 0;
                    }
                    else if (redWarrior->bombs.totalnum > 0)
                    {
                        redWarrior->nowWeapon[0] = 1;
                    }
                    else if (redWarrior->arrows.usedOnceNum > 0)
                    {
                        redWarrior->nowWeapon[0] = 2;
                    }
                    redWarrior->nowWeapon[1] = 0;
                }
            }
        }
    }
    void blueInCharge(){
        if (blueWarrior->totalWeaponNum > 0)
        {
            if (blueWarrior->nowWeapon[0] == 0)
            {
                sword::slash(blueWarrior, redWarrior);
                if (blueWarrior->nowWeapon[1] < blueWarrior->swords.totalnum - 1)
                {
                    blueWarrior->nowWeapon[1] += 1;
                }
                else
                {
                    if (blueWarrior->bombs.totalnum > 0)
                    {
                        blueWarrior->nowWeapon[0] = 1;
                    }
                    else if (blueWarrior->arrows.usedOnceNum > 0)
                    {
                        blueWarrior->nowWeapon[0] = 2;
                    }
                    else if (blueWarrior->arrows.usedZeroNum > 0)
                    {
                        blueWarrior->nowWeapon[0] = 3;
                    }
                    blueWarrior->nowWeapon[1] = 0;
                }
            }
            else if (blueWarrior->nowWeapon[0] == 1)
            {
                bomb::explode(blueWarrior, redWarrior);
                blueWarrior->totalWeaponNum -= 1;
                blueWarrior->bombs.totalnum -= 1;
                if (blueWarrior->bombs.totalnum > 0)
                {
                    blueWarrior->nowWeapon[1] = 0;
                }
                else
                {
                    if (blueWarrior->arrows.usedOnceNum > 0)
                    {
                        blueWarrior->nowWeapon[0] = 2;
                    }
                    else if (blueWarrior->arrows.usedZeroNum > 0)
                    {
                        blueWarrior->nowWeapon[0] = 3;
                    }
                    else if (blueWarrior->swords.totalnum > 0)
                    {
                        blueWarrior->nowWeapon[0] = 0;
                    }
                    blueWarrior->nowWeapon[1] = 0;
                }
            }
            else if (blueWarrior->nowWeapon[0] == 2)
            {
                arrow::shoot(blueWarrior, redWarrior);
                blueWarrior->totalWeaponNum -= 1;
                blueWarrior->arrows.totalnum -= 1;
                blueWarrior->arrows.usedOnceNum -= 1;
                if (blueWarrior->arrows.usedOnceNum > 0)
                {
                    blueWarrior->nowWeapon[1] = 0;
                }
                else
                {
                    if (blueWarrior->arrows.usedZeroNum > 0)
                    {
                        blueWarrior->nowWeapon[0] = 3;
                    }
                    else if (blueWarrior->swords.totalnum > 0)
                    {
                        blueWarrior->nowWeapon[0] = 0;
                    }
                    else if (blueWarrior->bombs.totalnum > 0)
                    {
                        blueWarrior->nowWeapon[0] = 1;
                    }
                    blueWarrior->nowWeapon[1] = 0;
                }
            }
            else if (blueWarrior->nowWeapon[0] == 3)
            {
                arrow::shoot(blueWarrior, redWarrior);
                blueWarrior->arrows.usedZeroNum -= 1;
                blueWarrior->arrows.usedOnceNum += 1;
                if (blueWarrior->arrows.usedZeroNum > 0)
                {
                    blueWarrior->nowWeapon[1] = 0;
                }
                else
                {
                    if (blueWarrior->swords.totalnum > 0)
                    {
                        blueWarrior->nowWeapon[0] = 0;
                    }
                    else if (blueWarrior->bombs.totalnum > 0)
                    {
                        blueWarrior->nowWeapon[0] = 1;
                    }
                    else if (blueWarrior->arrows.usedOnceNum > 0)
                    {
                        blueWarrior->nowWeapon[0] = 2;
                    }
                    blueWarrior->nowWeapon[1] = 0;
                }
            }
        }
    }
    void fight(){
        if (redWarrior==nullptr||blueWarrior==nullptr)
            return;
        int cnt = 0;
        if(ID&1==1)
            cnt = 0;
        else{
            cnt = 1;
        }
        prepareWeapon();
        while(blueWarrior->blood>0&&redWarrior->blood>0){
            int rblood = redWarrior->blood,rsword=redWarrior->swords.totalnum,rbomb=redWarrior->bombs.totalnum,rarrow1=redWarrior->arrows.usedOnceNum,rarrow2=redWarrior->arrows.usedZeroNum;
            int bblood = blueWarrior->blood, bsword = blueWarrior->swords.totalnum, bbomb = blueWarrior->bombs.totalnum, barrow1 = blueWarrior->arrows.usedOnceNum, barrow2 = blueWarrior->arrows.usedZeroNum;
            if(cnt%2==0){
                redInCharge();
                if(blueWarrior->blood>0){
                    blueInCharge();
                }
            }
            else{
                blueInCharge();
                if(redWarrior->blood>0){
                    redInCharge();
                }
            }
            cnt += 2;
            bool endtag = rblood == redWarrior->blood && bblood == blueWarrior->blood &&
                          rsword == redWarrior->swords.totalnum && bsword == blueWarrior->swords.totalnum &&
                          rbomb == redWarrior->bombs.totalnum && bbomb == blueWarrior->bombs.totalnum &&
                          rarrow1 == redWarrior->arrows.usedOnceNum && barrow1 == blueWarrior->arrows.usedOnceNum &&
                          rarrow1 == redWarrior->arrows.usedOnceNum && barrow1 == blueWarrior->arrows.usedOnceNum;
            if(endtag&&redWarrior->bombs.totalnum==0&&redWarrior->arrows.totalnum==0&&blueWarrior->arrows.totalnum==0&&blueWarrior->bombs.totalnum==0)
                break;
        }
    }
    void printOutcome(){
        if(redWarrior->blood==0){
            if(blueWarrior->blood==0){
                printf("%03d:%02d both red %s %d and blue %s %d died in city %d\n",gametime/60,gametime%60, redWarrior->name, redWarrior->ID, blueWarrior->name, blueWarrior->ID, ID);
                delete redWarrior;
                delete blueWarrior;
                redWarrior = nullptr;
                blueWarrior = nullptr;
            }
            else{
                blueWarrior->robTrophy(redWarrior);
                printf("%03d:%02d blue %s %d killed red %s %d in city %d remaining %d elements\n", gametime / 60, gametime % 60, blueWarrior->name, blueWarrior->ID, redWarrior->name, redWarrior->ID, ID, blueWarrior->blood);
                delete redWarrior;
                redWarrior = nullptr;
                if(strcmp(blueWarrior->name,"dragon")==0){
                    printf("%03d:%02d blue dragon %d yelled in city %d\n", gametime / 60, gametime % 60, blueWarrior->ID, ID);
                }
            }
        }
        else{
            if(blueWarrior->blood==0){
                redWarrior->robTrophy(blueWarrior);
                printf("%03d:%02d red %s %d killed blue %s %d in city %d remaining %d elements\n", gametime / 60, gametime % 60, redWarrior->name, redWarrior->ID, blueWarrior->name, blueWarrior->ID, ID, redWarrior->blood);
                delete blueWarrior;
                blueWarrior = nullptr;
                if (strcmp(redWarrior->name, "dragon") == 0)
                {
                    printf("%03d:%02d red dragon %d yelled in city %d\n", gametime / 60, gametime % 60, redWarrior->ID, ID);
                }
            }
            else{
                printf("%03d:%02d both red %s %d and blue %s %d were alive in city %d\n", gametime / 60, gametime % 60, redWarrior->name, redWarrior->ID, blueWarrior->name, blueWarrior->ID, ID);
                if (strcmp(redWarrior->name, "dragon") == 0)
                {
                    printf("%03d:%02d red dragon %d yelled in city %d\n", gametime / 60, gametime % 60, redWarrior->ID, ID);
                }
                if (strcmp(blueWarrior->name, "dragon") == 0)
                {
                    printf("%03d:%02d blue dragon %d yelled in city %d\n", gametime / 60, gametime % 60, blueWarrior->ID, ID);
                }
            }
        }
    }
};
void redmarch(castle* nowCastle,int citys){
    if(nowCastle->preCastle!=nullptr){
        nowCastle->redWarrior_tmp = nowCastle->redWarrior;
        nowCastle->redWarrior = nowCastle->preCastle->redWarrior_tmp;
        nowCastle->preCastle->redWarrior_tmp = nullptr;
        if(nowCastle->redWarrior==nullptr)
            return;
        if(strcmp(nowCastle->redWarrior->name,"iceman")==0){
            nowCastle->redWarrior->blood = max(0, nowCastle->redWarrior->blood - nowCastle->redWarrior->blood / 10);
        }
        if (strcmp(nowCastle->redWarrior->name, "lion") == 0)
        {
            lion *tmp = (lion *)nowCastle->redWarrior;
            tmp->loyalty -= tmp->fear;
        }
        if(nowCastle->redWarrior->blood==0){
            delete nowCastle->redWarrior;
            nowCastle->redWarrior = nullptr;
            return;
        }
        if(nowCastle->ID==citys+1){
            printf("%03d:%02d red %s %d reached blue headquarter with %d elements and force %d\n", gametime / 60, gametime % 60, nowCastle->redWarrior->name, nowCastle->redWarrior->ID, nowCastle->redWarrior->blood, nowCastle->redWarrior->attack_ability);
            printf("%03d:%02d blue headquarter was taken\n", gametime / 60, gametime % 60);
        }
        else
            printf("%03d:%02d red %s %d marched to city %d with %d elements and force %d\n", gametime / 60, gametime % 60, nowCastle->redWarrior->name, nowCastle->redWarrior->ID, nowCastle->ID, nowCastle->redWarrior->blood, nowCastle->redWarrior->attack_ability);
    }
    
}
void bluemarch(castle* nowCastle,int citys){
    if(nowCastle->nextCastle!=nullptr){
        nowCastle->blueWarrior = nowCastle->nextCastle->blueWarrior;
        nowCastle->nextCastle->blueWarrior = nullptr;
        if (nowCastle->blueWarrior == nullptr)
            return;
        if (strcmp(nowCastle->blueWarrior->name, "iceman") == 0)
        {
            nowCastle->blueWarrior->blood = max(0, nowCastle->blueWarrior->blood - nowCastle->blueWarrior->blood / 10);
        }
        if (strcmp(nowCastle->blueWarrior->name, "lion") == 0)
        {
            lion *tmp = (lion *)nowCastle->blueWarrior;
            tmp->loyalty -= tmp->fear;
        }
        if (nowCastle->blueWarrior->blood == 0)
        {
            delete nowCastle->blueWarrior;
            nowCastle->blueWarrior = nullptr;
            return;
        }
        if (nowCastle->ID == 0)
        {
            printf("%03d:%02d blue %s %d reached red headquarter with %d elements and force %d\n", gametime / 60, gametime % 60, nowCastle->blueWarrior->name, nowCastle->blueWarrior->ID, nowCastle->blueWarrior->blood, nowCastle->blueWarrior->attack_ability);
            printf("%03d:%02d red headquarter was taken\n", gametime / 60, gametime % 60);
        }
        else
            printf("%03d:%02d blue %s %d marched to city %d with %d elements and force %d\n", gametime / 60, gametime % 60, nowCastle->blueWarrior->name, nowCastle->blueWarrior->ID, nowCastle->ID, nowCastle->blueWarrior->blood, nowCastle->blueWarrior->attack_ability);
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
        int blood = 0, citys = 0, dloyalty = 0,span=0,
            db = 0, nb = 0, ib = 0, lb = 0, wb = 0, 
            datk = 0, natk = 0, iatk = 0, latk = 0, watk = 0;
        scanf("%d%d%d%d%d%d%d%d%d%d%d%d%d%d",&blood,&citys,&dloyalty,&span,&db,&nb,&ib,&lb,&wb,&datk,&natk,&iatk,&latk,&watk);
        for (int i = 0; i <= citys + 1;++i){
            castles[i].ID = i;
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
        cout << "Case " << n1 - n <<":"<< endl;
        while(gametime<=span){
            if(gametime%60==0){
                bool flag = 0;
                if(!red.stopmaking){
                    if(red.blood>=red.sequence[(red.loopptr)%5]->blood){
                        red.IDofNowMakingWarrior += 1;
                        warrior &tmp = *red.sequence[(red.loopptr) % 5];
                        printf("%03d:%02d red %s %d born\n",gametime/60,gametime%60,tmp.name,red.IDofNowMakingWarrior);
                        if (strcmp(tmp.name,"dragon")==0)
                        {
                            red.blood -= redtroop::dragon_attr[0];
                            dragon *pdragon = new dragon('r', red.IDofNowMakingWarrior);
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
                            printf("Its loyalty is %d\n",plion->loyalty);
                        }
                        else{
                            red.blood -= redtroop::wolf_attr[0];
                            wolf *pwolf = new wolf('r', red.IDofNowMakingWarrior);
                            castles[0].redWarrior_tmp = pwolf;
                        }
                        red.loopptr = (red.loopptr+ 1) % 5;
                        flag = 1;
                    }
                    if(!flag){
                        red.stopmaking = 1;
                    }
                }
                flag = 0;
                if (!blue.stopmaking)
                {
                    if (blue.blood >= blue.sequence[(blue.loopptr) % 5]->blood)
                    {
                        blue.IDofNowMakingWarrior += 1;
                        warrior &tmp = *blue.sequence[(blue.loopptr) % 5];
                        printf("%03d:%02d blue %s %d born\n",
                               gametime/60,gametime%60, tmp.name, blue.IDofNowMakingWarrior);
                        if (strcmp(tmp.name, "dragon") == 0)
                        {
                            blue.blood -= bluetroop::dragon_attr[0];
                            dragon *pdragon = new dragon('b', blue.IDofNowMakingWarrior);
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
                            printf("Its loyalty is %d\n", plion->loyalty);
                        }
                        else
                        {
                            blue.blood -= bluetroop::wolf_attr[0];
                            wolf *pwolf = new wolf('b', blue.IDofNowMakingWarrior);
                            castles[citys+1].blueWarrior = pwolf;
                        }
                        blue.loopptr = (blue.loopptr+ 1) % 5;
                        flag = 1;
                    }
                    if (!flag)
                    {
                        blue.stopmaking = 1;
                    }
                }
            }
            else if(gametime%60==5){
                for (int i = 0; i <= citys + 1; ++i)
                {
                    if (castles[i].redWarrior != nullptr)
                    {
                        if (strcmp(castles[i].redWarrior->name, "lion") == 0)
                        {
                            lion *plion = (lion *)castles[i].redWarrior;
                            if (plion->loyalty <= 0)
                            {
                                printf("%03d:%02d red lion %d ran away\n", gametime / 60, gametime % 60, plion->ID);
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
                                printf("%03d:%02d blue lion %d ran away\n", gametime / 60, gametime % 60, plion->ID);
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
                if(castles[0].blueWarrior!=nullptr){
                    gameover = 1;
                }
                if (castles[citys+1].redWarrior != nullptr)
                {
                    gameover = 1;
                }
                if(gameover==1)
                    break;
            }
            else if(gametime%60==35){
                for (int i = 0; i <= citys + 1;++i){
                    if(castles[i].redWarrior&&castles[i].blueWarrior)
                        castles[i].wolfRob();
                }
            }
            else if(gametime%60==40){
                for (int i = 0; i <= citys + 1;++i){
                    if(castles[i].blueWarrior&&castles[i].redWarrior){
                        castles[i].fight();
                        castles[i].printOutcome();
                    }
                }
            }
            else if(gametime%60==50){
                printf("%03d:%02d %d elements in red headquarter\n", gametime / 60, gametime % 60, red.blood);
                printf("%03d:%02d %d elements in blue headquarter\n", gametime / 60, gametime % 60, blue.blood);
            }
            else if(gametime%60==55){
                for (int i = 0; i <= citys + 1;++i){
                    if(castles[i].redWarrior){
                        printf("%03d:%02d red %s %d has %d sword %d bomb %d arrow and %d elements\n", gametime / 60, gametime % 60,castles[i].redWarrior->name,castles[i].redWarrior->ID, castles[i].redWarrior->swords.totalnum, castles[i].redWarrior->bombs.totalnum, castles[i].redWarrior->arrows.totalnum, castles[i].redWarrior->blood);
                    }
                    if (castles[i].blueWarrior){
                        printf("%03d:%02d blue %s %d has %d sword %d bomb %d arrow and %d elements\n", gametime / 60, gametime % 60, castles[i].blueWarrior->name, castles[i].blueWarrior->ID, castles[i].blueWarrior->swords.totalnum, castles[i].blueWarrior->bombs.totalnum, castles[i].blueWarrior->arrows.totalnum, castles[i].blueWarrior->blood);
                    }
                }
            }
            gametime += 5;
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
        }
    }
    system("pause");
    return 0;
}
