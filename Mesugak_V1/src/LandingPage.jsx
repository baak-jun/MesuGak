import React, { useState } from 'react';
import { Activity, Shield, TrendingUp, Lock, Users, Monitor, Code, ChevronLeft, ChevronRight } from 'lucide-react';

import imgBuy from './assets/buy_signal.png';
import imgSqueeze from './assets/squeeze.png';
import imgNormal from './assets/normal.png';

const LandingPage = ({ onLogin }) => {
  const [activeTab, setActiveTab] = useState('home'); // 'home', 'screenshots', 'team'
  const [currentSlide, setCurrentSlide] = useState(0);

  const slides = [
    {
      id: 1,
      title: "매수각 (Buy Signal)",
      desc: "에너지 응축 후 상단을 강력하게 돌파하는 시점을 포착합니다.",
      icon: <TrendingUp className="w-16 h-16 text-red-500" />,
      color: "text-red-500",
      bgColor: "bg-red-500/10",
      borderColor: "border-red-500/30",
      image: imgBuy
    },
    {
      id: 2,
      title: "응축 (Squeeze)",
      desc: "폭발적인 시세 분출을 위해 에너지를 모으는 고요한 구간입니다.",
      icon: <Activity className="w-16 h-16 text-yellow-400" />,
      color: "text-yellow-400",
      bgColor: "bg-yellow-500/10",
      borderColor: "border-yellow-500/30",
      image: imgSqueeze
    },
    {
      id: 3,
      title: "일반 흐름 (Normal)",
      desc: "특이 사항이 없는 일반적인 시장 상황입니다.",
      icon: <Monitor className="w-16 h-16 text-slate-500" />,
      color: "text-slate-400",
      bgColor: "bg-slate-800",
      borderColor: "border-slate-700",
      image: imgNormal
    }
  ];

  const nextSlide = () => {
    setCurrentSlide((prev) => (prev + 1) % slides.length);
  };

  const prevSlide = () => {
    setCurrentSlide((prev) => (prev - 1 + slides.length) % slides.length);
  };

  const renderContent = () => {
    switch(activeTab) {
      case 'home':
        return (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-6 mt-10 animate-fade-in">
            <div className="bg-yellow-500/10 text-yellow-400 px-3 py-1 rounded-full text-xs font-bold mb-6 border border-yellow-500/20">
                PRIVATE BETA ACCESS ONLY
            </div>
            <h1 className="text-4xl md:text-6xl font-bold mb-6 leading-tight">
                시장의 <span className="text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 to-orange-500">매수각</span>을 <br/>
                날카롭게 포착하세요.
            </h1>
            <p className="text-slate-400 text-lg md:text-xl max-w-2xl mb-10 leading-relaxed">
                MesuGak은 볼린저 밴드와 거래량을 분석하여 <br className="hidden md:block"/>
                폭발적인 시세 분출 전의 <strong>'응축(Squeeze)'</strong> 구간을 탐지하는 AI 스캐너입니다.
            </p>
            
            <button 
                onClick={onLogin}
                className="px-8 py-4 bg-yellow-500 hover:bg-yellow-400 text-slate-900 text-lg font-bold rounded-xl shadow-lg shadow-yellow-500/20 transition-all transform hover:scale-105"
            >
                지금 시작하기
            </button>

            {/* Features */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-20 max-w-5xl w-full">
                <div className="bg-slate-800/50 p-6 rounded-2xl border border-slate-700 hover:border-blue-500/50 transition-colors">
                    <div className="w-12 h-12 bg-blue-500/20 rounded-xl flex items-center justify-center mb-4 text-blue-400 mx-auto">
                        <TrendingUp />
                    </div>
                    <h3 className="text-lg font-bold mb-2">실시간 패턴 감지</h3>
                    <p className="text-slate-400 text-sm">에너지 응축(Squeeze)과 강력한 돌파(Breakout) 신호를 실시간으로 포착합니다.</p>
                </div>
                <div className="bg-slate-800/50 p-6 rounded-2xl border border-slate-700 hover:border-purple-500/50 transition-colors">
                    <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center mb-4 text-purple-400 mx-auto">
                        <Activity />
                    </div>
                    <h3 className="text-lg font-bold mb-2">스마트 밴드폭 정렬</h3>
                    <p className="text-slate-400 text-sm">가장 에너지가 응축된 종목부터 우선적으로 보여주어 기회를 놓치지 않습니다.</p>
                </div>
                <div className="bg-slate-800/50 p-6 rounded-2xl border border-slate-700 hover:border-emerald-500/50 transition-colors">
                    <div className="w-12 h-12 bg-emerald-500/20 rounded-xl flex items-center justify-center mb-4 text-emerald-400 mx-auto">
                        <Shield />
                    </div>
                    <h3 className="text-lg font-bold mb-2">비공개 운영</h3>
                    <p className="text-slate-400 text-sm">
                        개인 연구 목적으로 비공개 운영 중입니다.<br/>
                        이용 문의: <a href="mailto:or_not_official@naver.com" className="text-emerald-400 hover:underline">or_not_official@naver.com</a>
                    </p>
                </div>
            </div>

            {/* Disclaimer */}
            <div className="mt-20 border-t border-slate-800 pt-8 max-w-3xl">
                <h4 className="text-slate-500 font-bold mb-2 text-sm">법적 고지 및 이용 안내</h4>
                <p className="text-slate-600 text-xs leading-relaxed mb-4">
                    본 서비스가 제공하는 모든 정보는 투자 판단을 위한 참고 자료일 뿐이며, 투자의 최종 책임은 이용자 본인에게 있습니다. <br/>
                    MesuGak은 제공된 정보의 정확성이나 완전성을 보장하지 않으며, 투자 손실에 대해 책임을 지지 않습니다.
                </p>
                <p className="text-slate-600 text-xs leading-relaxed">
                    현재 본 사이트는 개인적인 연구 및 이용을 위해 <strong>비공개(Private)</strong>로 운영되고 있습니다. <br/>
                    사용 권한 요청이나 문의사항이 있으신 경우 <a href="mailto:or_not_official@naver.com" className="text-slate-500 underline hover:text-slate-400">or_not_official@naver.com</a> 으로 연락 주시기 바랍니다.
                </p>
            </div>
          </div>
        );
      
      case 'screenshots':
        const slide = slides[currentSlide];
        return (
          <div className="flex-1 flex flex-col items-center p-6 mt-4 max-w-7xl mx-auto w-full animate-fade-in text-center">
            <h2 className="text-3xl font-bold mb-4">서비스 미리보기</h2>
            <p className="text-slate-400 mb-6">MesuGak의 주요 분석 패턴을 확인해보세요.</p>
            
            <div className="relative w-full min-h-[600px] flex items-center justify-center py-10">
                
                {/* Left Button */}
                <button 
                    onClick={prevSlide}
                    className="absolute left-0 z-10 p-3 bg-slate-800/50 hover:bg-slate-700 text-white rounded-full backdrop-blur-sm transition-all -translate-x-2 md:-translate-x-12"
                >
                    <ChevronLeft className="w-8 h-8" />
                </button>

                {/* Main Slide Content */}
                <div className={`relative w-full rounded-2xl border ${slide.borderColor} ${slide.bgColor} flex flex-col items-center justify-center p-8 shadow-2xl transition-all duration-300`}>
                    <div className="flex flex-col md:flex-row items-center gap-6 mb-8 text-center md:text-left">
                        {slide.icon}
                        <div>
                            <h3 className={`text-3xl font-bold ${slide.color} mb-2`}>
                                {slide.title}
                            </h3>
                            <p className="text-slate-300 text-lg max-w-2xl">
                                {slide.desc}
                            </p>
                        </div>
                    </div>
                    
                    {/* Real Screenshot Image */}
                    <div className="w-full aspect-video bg-black/40 rounded-xl overflow-hidden border-2 border-slate-600/30 shadow-2xl mb-4">
                        <img 
                            src={slide.image} 
                            alt={slide.title} 
                            className="w-full h-full object-cover transform hover:scale-105 transition-transform duration-700"
                        />
                    </div>
                    
                    <p className="text-slate-500 text-xs text-center w-full">
                        * 본 예시 화면은 2026년 2월 3일에 촬영된 사진으로, 현재의 시장 흐름을 반영하지 않습니다.
                    </p>
                </div>

                {/* Right Button */}
                <button 
                    onClick={nextSlide}
                    className="absolute right-0 z-10 p-3 bg-slate-800/50 hover:bg-slate-700 text-white rounded-full backdrop-blur-sm transition-all translate-x-2 md:translate-x-12"
                >
                    <ChevronRight className="w-8 h-8" />
                </button>
            </div>

            {/* Pagination Dots */}
            <div className="flex justify-center gap-3 mt-8">
                {slides.map((_, index) => (
                    <button
                        key={index}
                        onClick={() => setCurrentSlide(index)}
                        className={`w-3 h-3 rounded-full transition-all ${
                            currentSlide === index 
                            ? 'bg-yellow-500 w-8' 
                            : 'bg-slate-700 hover:bg-slate-600'
                        }`}
                    />
                ))}
            </div>
          </div>
        );

      case 'team':
        return (
          <div className="flex-1 flex flex-col items-center justify-center p-6 mt-10 max-w-4xl mx-auto w-full animate-fade-in">
             <h2 className="text-3xl font-bold mb-10">MesuGak Dev Team</h2>
             
             <div className="w-full bg-slate-800 rounded-2xl border border-slate-700 p-8 flex flex-col md:flex-row items-center gap-8">
                <div className="w-32 h-32 bg-slate-700 rounded-full flex items-center justify-center border-4 border-slate-600 shadow-xl">
                    <Code className="w-16 h-16 text-slate-400" />
                </div>
                <div className="text-center md:text-left flex-1">
                    <h3 className="text-2xl font-bold text-white mb-2">Team Or_Not</h3>
                    <p className="text-yellow-400 font-medium mb-4">Lead Developer & Operator</p>
                    <p className="text-slate-300 leading-relaxed mb-6">
                        "데이터는 거짓말을 하지 않습니다. <br/>
                        우리는 시장의 소음을 제거하고 본질적인 신호만을 찾아냅니다."
                    </p>
                    <div className="flex gap-4 justify-center md:justify-start">
                        <a href="mailto:or_not_official@naver.com" className="px-4 py-2 bg-slate-700 rounded-lg text-sm text-slate-300 hover:bg-slate-600 transition-colors">
                            Contact
                        </a>
                        <button className="px-4 py-2 bg-slate-700 rounded-lg text-sm text-slate-300 hover:bg-slate-600 transition-colors cursor-not-allowed opacity-50">
                            GitHub (Private)
                        </button>
                    </div>
                </div>
             </div>

             <div className="mt-12 text-center">
                <p className="text-slate-500 mb-2 font-medium">Tech Stack</p>
                <div className="flex gap-4 justify-center flex-wrap opacity-70">
                    <span className="px-3 py-1 bg-slate-800 rounded-full text-xs text-slate-400 border border-slate-700">React</span>
                    <span className="px-3 py-1 bg-slate-800 rounded-full text-xs text-slate-400 border border-slate-700">Firebase</span>
                    <span className="px-3 py-1 bg-slate-800 rounded-full text-xs text-slate-400 border border-slate-700">Python</span>
                    <span className="px-3 py-1 bg-slate-800 rounded-full text-xs text-slate-400 border border-slate-700">Pandas</span>
                    <span className="px-3 py-1 bg-slate-800 rounded-full text-xs text-slate-400 border border-slate-700">AWS EC2</span>
                </div>
             </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white flex flex-col font-sans">
      {/* Header */}
      <header className="px-6 py-4 flex flex-col md:flex-row justify-between items-center border-b border-slate-800 gap-4">
        <div className="flex items-center gap-2">
            <Activity className="text-yellow-400 w-6 h-6" />
            <span className="text-xl font-bold tracking-tight">MesuGak</span>
        </div>
        
        {/* Navigation Tabs */}
        <nav className="flex bg-slate-800/50 p-1 rounded-xl">
            <button 
                onClick={() => setActiveTab('home')}
                className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'home' ? 'bg-slate-700 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'}`}
            >
                소개
            </button>
            <button 
                onClick={() => setActiveTab('screenshots')}
                className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'screenshots' ? 'bg-slate-700 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'}`}
            >
                미리보기
            </button>
            <button 
                onClick={() => setActiveTab('team')}
                className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'team' ? 'bg-slate-700 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'}`}
            >
                개발진
            </button>
        </nav>

        <button 
            onClick={onLogin} 
            className="px-4 py-2 bg-yellow-500 hover:bg-yellow-400 text-slate-900 rounded-lg text-sm font-bold transition-all flex items-center gap-2 shadow-lg shadow-yellow-500/20"
        >
            <Lock className="w-4 h-4" /> 로그인
        </button>
      </header>

      {/* Main Content Area */}
      {renderContent()}
      
      <footer className="py-8 text-center text-slate-700 text-xs border-t border-slate-800 mt-auto">
        <p className="mb-2">MesuGak Intelligence Systems</p>
        <p>© 2026 MesuGak. All rights reserved.</p>
      </footer>
    </div>
  );
};

export default LandingPage;
