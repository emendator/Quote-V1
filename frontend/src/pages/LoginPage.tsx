import AuthShell from '../components/AuthShell';
import AuthFlipCard from '../components/AuthFlipCard';

const LoginPage = () => (
    <AuthShell>
        <AuthFlipCard initialSide="login" />
    </AuthShell>
);

export default LoginPage;
